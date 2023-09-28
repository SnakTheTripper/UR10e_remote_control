import asyncio
import sys
import json
import zmq.asyncio
import config
from asyncio.windows_events import WindowsSelectorEventLoopPolicy

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
page_init = None

rtde_frequency = config.rtde_frequency
rtde_period = 1 / config.rtde_frequency    # 0.002s for 500Hz

if config.rtde_frequency > 500:
    print("RTDE Update frequency cant be higher than 500Hz")
    rtde_period = 0.002     # for 500Hz
    rtde_frequency = 500

def calculate_opcua_freq_divider():     # based on RTDE and desired OPCUA frequency
    opcua_freq_divider = rtde_frequency / config.opcua_frequency
    if config.opcua_frequency > rtde_frequency:
        print(f"RTDE Update frequency: {rtde_frequency}")
        print("OPCUA Update frequency can't be higher than RTDE frequency!")
        opcua_freq_divider = 1
        print(f"OPCUA Update frequency set to RTDE frequency: {rtde_frequency}Hz")
    else:
        print(f"RTDE Update frequency: {rtde_frequency}Hz")
        print(f"OPCUA Update frequency: {config.opcua_frequency}Hz")

    return opcua_freq_divider

def initialize_zmq_connections():
    to_bridge_socket = context.socket(zmq.PUB)
    from_bridge_socket = context.socket(zmq.SUB)
    to_flask_socket = context.socket(zmq.PUB)
    from_flask_socket = context.socket(zmq.SUB)
    to_opcua_socket = context.socket(zmq.PUB)
    from_opcua_socket = context.socket(zmq.SUB)
    try:    # com with UR10e_bridge
        to_bridge_socket.connect(f"tcp://{config.ip_address_bridge}:{config.port_mw_b}")
        from_bridge_socket.connect(f"tcp://{config.ip_address_bridge}:{config.port_b_mw}")
        print('\033[32mUR10e Bridge ports bound!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to UR10e Bridge! {e}\033[0m")

    try:    # com with Flask Server
        to_flask_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_mw_f}")
        from_flask_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_f_mw}")
        print('\033[32mFlask Server ports bound!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to Flask Server! {e}\033[0m")

    try:    # com with OPCUA Server
        to_opcua_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_mw_op}")
        from_opcua_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_op_mw}")
        print('\033[32mOPCUA Server ports bound!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to OPCUA Server! {e}\033[0m")

    print(
        f'Publish on port: {config.port_mw_f} & {config.port_mw_b} & {config.port_op_mw}\n'
        f'Listening on port: {config.port_f_mw} & {config.port_b_mw} & {config.port_mw_op}')

    return to_opcua_socket, to_bridge_socket, to_flask_socket, from_bridge_socket, from_opcua_socket, from_flask_socket

class UR10e:
    def __init__(self):
        self.current_joint = [0.0]*6
        self.target_joint = [0.0]*6

        self.current_tcp = [0.0]*6
        self.target_tcp = [0.0]*6

        # represents last used move_type
        self.move_type = 1  # 0 = linear 1 = joint
        self.joint_speed = 0.1
        self.joint_accel = 0.1
        self.linear_speed = 0.1
        self.linear_accel = 0.1
        self.is_moving = False
        self.STOP = False

        self.input_bit_0 = 0.0
        self.input_bit_1 = 0.0
        self.input_bit_2 = 0.0
        self.input_bit_3 = 0.0
        self.input_bit_4 = 0.0
        self.input_bit_5 = 0.0
        self.input_bit_6 = 0.0
        self.input_bit_7 = 0.0

        self.output_bit_0 = 0.0
        self.output_bit_1 = 0.0
        self.output_bit_2 = 0.0
        self.output_bit_3 = 0.0
        self.output_bit_4 = 0.0
        self.output_bit_5 = 0.0
        self.output_bit_6 = 0.0
        self.output_bit_7 = 0.0

    def update_local_dataset(self, data_dictionary):
        for key, value in data_dictionary.items():
            setattr(self, key, value)

    def gather_to_send(self):   # send all attributes
        return self.__dict__

local_robot_state = UR10e()
context = zmq.asyncio.Context()
(to_opcua_socket,
 to_bridge_socket,
 to_flask_socket,
 from_bridge_socket,
 from_opcua_socket,
 from_flask_socket) = initialize_zmq_connections()

async def update_opcua():
    # serializes the dictionary of robot attributes
    serialized_message = json.dumps(local_robot_state.gather_to_send()).encode()  # dictionary of robot attributes
    # print('sending package to opcua server')
    await to_opcua_socket.send_multipart([b"update_package", serialized_message])

async def send_to_flask(pub_socket, topic, message, last_moving_state): # FW current to Flask
    if local_robot_state.is_moving or page_init:
        await pub_socket.send_multipart([topic, message])
    elif last_moving_state and not local_robot_state.is_moving:
        await pub_socket.send_multipart([topic, message])

# local dataset AND opcua
async def update_data(decoded_message, i, opcua_freq_divider):
    local_robot_state.update_local_dataset(decoded_message)
    if i >= opcua_freq_divider:
        await update_opcua()
        i = 1
    else:
        i += 1
    return i

async def receive_from_bridge(pub_socket, sub_socket):
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"Joint_States")
    opcua_freq_divider = calculate_opcua_freq_divider()
    global page_init    # changes to True on webpage is loaded by a client
    last_moving_state = False
    i = 1
    while True:
        topic, message = await sub_socket.recv_multipart()
        decoded_message = json.loads(message.decode())
        print(f'from bridge: {decoded_message}')

        last_moving_state = await send_to_flask(pub_socket, topic, message, last_moving_state)

        i = await update_data(decoded_message, i, opcua_freq_divider)     # updates local AND opcua (opcua with lower freq.)
        if last_moving_state:   # one last call to keep opcua up to date
            await update_opcua()

        await asyncio.sleep(rtde_period)


async def zmq_forward_flask_to_bridge(pub_socket, sub_socket):
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"page_init")
    global page_init
    while True:
        [topic, message] = await sub_socket.recv_multipart()
        if topic == b"Move_Commands":
            await pub_socket.send_multipart([topic, message])   # forward quickly to bridge
            print(message.decode())
        elif topic == b"page_init":     # set page_init to True -> current data flow opens from bridge to flask
            page_init = True
            await asyncio.sleep(0.2)   # might need more time to work properly
            page_init = False

        await asyncio.sleep(0.002)


async def main():
    await asyncio.gather(
        receive_from_bridge(to_flask_socket, from_bridge_socket),
        zmq_forward_flask_to_bridge(to_bridge_socket, from_flask_socket)
    )

if __name__ == "__main__":
    asyncio.run(main())
