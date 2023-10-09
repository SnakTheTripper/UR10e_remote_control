import asyncio
import sys
import json
import zmq.asyncio
import config
from asyncio.windows_events import WindowsSelectorEventLoopPolicy

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Set then check Update frequency for RTDE & OPCUA

rtde_frequency = config.rtde_frequency
rtde_period = 1 / config.rtde_frequency     # 0.002s for 500Hz

opcua_frequency = config.opcua_frequency
opcua_period = 1 / config.opcua_frequency

if rtde_frequency > 500:
    print("RTDE Update frequency can not be higher than 500Hz")
    rtde_period = 0.002  # for 500Hz
    rtde_frequency = 500

if opcua_frequency > rtde_frequency:
    print('OPCUA Update frequency can not be higher than RTDE Update frequency')
    opcua_period = rtde_period
    opcua_frequency = rtde_frequency

def initialize_zmq_connections(context):
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
        self.control_mode = 'flask'
        self.joint_speed = 0.1
        self.joint_accel = 0.1
        self.linear_speed = 0.1
        self.linear_accel = 0.1
        self.is_moving = False
        self.STOP = False

        self.input_bit_0 = 0
        self.input_bit_1 = 0
        self.input_bit_2 = 0
        self.input_bit_3 = 0
        self.input_bit_4 = 0
        self.input_bit_5 = 0
        self.input_bit_6 = 0
        self.input_bit_7 = 0

        self.output_bit_0 = 0
        self.output_bit_1 = 0
        self.output_bit_2 = 0
        self.output_bit_3 = 0
        self.output_bit_4 = 0
        self.output_bit_5 = 0
        self.output_bit_6 = 0
        self.output_bit_7 = 0

        self.page_init = False

    def update_local_dataset(self, data_dictionary):
        for key, value in data_dictionary.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f'Tried updating {key}, but it not an attribute of the object!')

    def gather_to_send_all(self):   # send all attributes
        return {key: value for key, value in self.__dict__.items() if
                key not in ['page_init']}

    def gather_to_send_no_control(self):   # send all attributes
        return {key: value for key, value in self.__dict__.items() if
                key not in ['target_joint',
                            'target_tcp',
                            'move_type',
                            'joint_speed',
                            'joint_accel',
                            'linear_speed',
                            'linear_accel',
                            'page_init']}

class FlaskHandler:
    def __init__(self, to_flask, from_flask, to_bridge, local_ur):
        self.to_flask_sock = to_flask
        self.to_bridge_sock = to_bridge

        self.from_flask_sock = from_flask
        self.from_flask_sock.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
        self.from_flask_sock.setsockopt(zmq.SUBSCRIBE, b"page_init")

        self.local_ur10 = local_ur

    async def send(self):
        # send updates to Flask
        last_drops = 10
        while True:
            if last_drops > 0 or self.local_ur10.page_init:
                topic = b"Joint_States"
                serialized_message = None

                if self.local_ur10.control_mode == 'flask':
                    serialized_message = json.dumps(self.local_ur10.gather_to_send_no_control()).encode()
                elif self.local_ur10.control_mode == 'opcua':
                    serialized_message = json.dumps(self.local_ur10.gather_to_send_all()).encode()

                try:
                    await self.to_flask_sock.send_multipart([topic, serialized_message])
                except Exception as e:
                    print(f'Can not send update to Flask: {e}')

                if not self.local_ur10.is_moving:
                    last_drops -= 1     # decrease only when not moving

            if self.local_ur10.is_moving:
                last_drops = 10

            await asyncio.sleep(rtde_period)

    async def receive(self):
        # receive from Flask
        while True:
            if self.local_ur10.control_mode == 'flask':
                topic, serialized_message = await self.from_flask_sock.recv_multipart()

                if topic == b'Move_Commands':
                    # quickly forward to bridge
                    await self.to_bridge_sock.send_multipart([topic, serialized_message])
                    # then unpack and update local dataset
                    self.local_ur10.update_local_dataset(json.loads(serialized_message.decode()))
                elif topic == b'page_init':
                    self.local_ur10.page_init = True
                    await asyncio.sleep(5 * rtde_period)
                    self.local_ur10.page_init = False
            elif self.local_ur10.control_mode == 'opcua':
                await asyncio.sleep(1)  # Sleep a bit when not in flask mode

class OpcuaHandler:
    def __init__(self, to_opcua, from_opcua, to_bridge, local_ur):
        self.to_opcua_sock = to_opcua
        self.to_bridge_sock = to_bridge

        self.from_opcua_sock = from_opcua
        self.from_opcua_sock.setsockopt(zmq.SUBSCRIBE, b"opcua_command")

        self.local_ur10 = local_ur

    async def send(self):
        # send to OPCUA from MW database
        serialized_message = None
        while True:
            if self.local_ur10.control_mode == 'flask':
                serialized_message = json.dumps(self.local_ur10.gather_to_send_all()).encode()  # dictionary of robot attributes
            elif self.local_ur10.control_mode == 'opcua':
                serialized_message = json.dumps(self.local_ur10.gather_to_send_no_control()).encode()

            await self.to_opcua_sock.send_multipart([b"update_package", serialized_message])
            await asyncio.sleep(opcua_period)

    async def receive(self):        # receive from OPCUA
        while True:
            if self.local_ur10.control_mode == 'opcua':
                [topic, serialized_message] = await self.from_opcua_sock.recv_multipart()
                print('msg from opcua arrived to MW')

                # quickly forward to bridge
                await self.to_bridge_sock.send_multipart([topic, serialized_message])
                # then unpack and update local dataset
                self.local_ur10.update_local_dataset(json.loads(serialized_message.decode()))

            elif self.local_ur10.control_mode == 'flask':
                await asyncio.sleep(1)      # wait a bit if not in opcua control

async def receive_from_bridge(from_bridge_sock, local_ur10):
    from_bridge_sock.setsockopt(zmq.SUBSCRIBE, b'Joint_States')
    while True:
        topic, serialized_message = await from_bridge_sock.recv_multipart()
        local_ur10.update_local_dataset(json.loads(serialized_message.decode()))    # blocking command

        await asyncio.sleep(rtde_period)
async def main():
    local_ur10 = UR10e()

    context = zmq.asyncio.Context()
    (to_opcua_socket,
     to_bridge_socket,
     to_flask_socket,
     from_bridge_socket,
     from_opcua_socket,
     from_flask_socket) = initialize_zmq_connections(context)

    flask_handler = FlaskHandler(to_flask_socket, from_flask_socket, to_bridge_socket, local_ur10)
    opcua_handler = OpcuaHandler(to_opcua_socket, from_opcua_socket, to_bridge_socket, local_ur10)

    await asyncio.gather(flask_handler.send(),
                         flask_handler.receive(),
                         opcua_handler.send(),
                         opcua_handler.receive(),
                         receive_from_bridge(from_bridge_socket, local_ur10))

if __name__ == "__main__":
    asyncio.run(main())
