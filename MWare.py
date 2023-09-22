import asyncio
import sys
import json
import zmq.asyncio
import config
from asyncio.windows_events import WindowsSelectorEventLoopPolicy

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

rtde_frequency = config.rtde_frequency
rtde_period = 1 / config.rtde_frequency    # 0.002s for 500Hz

if config.rtde_frequency > 500:
    print("RTDE Update frequency cant be higher than 500Hz")
    rtde_period = 0.002     # for 500Hz
    rtde_frequency = 500

class UR10e:
    def __init__(self):
        self.current_joint_positions = [0.0]*6
        self.target_joint_positions = [0.0]*6
        self.joint_speed = 0.0
        self.joint_accel = 0.0

        self.current_joint_positions = [0.0]*6
        self.target_joint_positions = [0.0]*6
        self.tcp_speed = 0.0
        self.tcp_accel = 0.0

        # add more attributes here

        # Calculate the opcua_freq_divider as soon as the object is created
        self.opcua_freq_divider = 10    # base value
        self.calculate_opcua_freq_divider()

    def calculate_opcua_freq_divider(self):
        self.opcua_freq_divider = rtde_frequency / config.opcua_frequency
        if config.opcua_frequency > rtde_frequency:
            print(f"RTDE Update frequency: {rtde_frequency}")
            print("OPCUA Update frequency can't be higher than RTDE frequency!")
            self.opcua_freq_divider = 1
            print(f"OPCUA Update frequency set to RTDE frequency: {rtde_frequency}Hz")
        else:
            print(f"RTDE Update frequency: {rtde_frequency}Hz")
            print(f"OPCUA Update frequency: {config.opcua_frequency}Hz")

    def update(self, param_json_str):
        try:
            param_dict = json.loads(param_json_str)
            for key, value in param_dict.items():
                setattr(self, key, value)
        except json.JSONDecodeError:
            print("Could not decode JSON string.")

async def zmq_forward_bridge_to_flask(pub_socket, sub_socket, robot_object):
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"Joint_States")
    i = 0
    while True:
        topic, message = await sub_socket.recv_multipart()
        await pub_socket.send_multipart([topic, message])

        # update OPCUA no matter if moving or not

        if i > robot_object.opcua_freq_divider:
            robot_object.update(message.decode())
            print('current position updated')
            i = 0
        else:
            i += 1

        await asyncio.sleep(rtde_period)


async def zmq_forward_flask_to_bridge(pub_socket, sub_socket, robot_object):
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
    i = 0
    while True:
        [topic, message] = await sub_socket.recv_multipart()
        await pub_socket.send_multipart([topic, message])   # forward quickly to bridge
        print(message.decode)
        # if i > robot_object.opcua_freq_divider:           # maybe not needed as commands come slowly
        #     robot_object.update(message.decode())
        #     i = 0
        # else:
        #     i += 1

        await asyncio.sleep(0.002)


async def main():
    robot_object = UR10e()
    
    context = zmq.asyncio.Context()
    
    to_bridge_socket = context.socket(zmq.PUB)
    from_bridge_socket = context.socket(zmq.SUB)
    to_flask_socket = context.socket(zmq.PUB)
    from_flask_socket = context.socket(zmq.SUB)
    try:
        to_bridge_socket.connect(f"tcp://{config.ip_address_bridge}:{config.port_mw_b}")
        from_bridge_socket.connect(f"tcp://{config.ip_address_bridge}:{config.port_b_mw}")

        to_flask_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_mw_f}")
        from_flask_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_f_mw}")
    except:
        sys.exit("Can't connect to UR10e Bridge or Flask server!")
    print(f'Publish on port: {config.port_f_mw}\nListening on port: {config.port_mw_f}')

    await asyncio.gather(
        zmq_forward_bridge_to_flask(to_flask_socket, from_bridge_socket, robot_object),
        zmq_forward_flask_to_bridge(to_bridge_socket, from_flask_socket, robot_object)
    )

if __name__ == "__main__":
    asyncio.run(main())
