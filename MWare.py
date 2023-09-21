import asyncio
import sys
import json
import zmq.asyncio
import config
from asyncio.windows_events import WindowsSelectorEventLoopPolicy

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

class ur10e:
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

        if i > config.rate_limiter_for_MW_data_update:
            robot_object.update(message.decode())
            i = 0
        else:
            i += 1

        await asyncio.sleep(0.002)


async def zmq_forward_flask_to_bridge(pub_socket, sub_socket, robot_object):
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
    i = 0
    while True:
        [topic, message] = await sub_socket.recv_multipart()
        await pub_socket.send_multipart([topic, message])   # forward quickly to bridge
        print(message.decode)
        if i > config.rate_limiter_for_MW_data_update:
            robot_object.update(message.decode())
            i = 0
        else:
            i += 1

        await asyncio.sleep(0.002)


async def main():
    robot_object = ur10e()
    
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
        sys.exit("Can't connect to MiddleWare!")
    print(f'Connected to middleware!\nPublish on port: {config.port_f_mw}\nListening on port: {config.port_mw_f}')

    await asyncio.gather(
        zmq_forward_bridge_to_flask(to_flask_socket, from_bridge_socket, robot_object),
        zmq_forward_flask_to_bridge(to_bridge_socket, from_flask_socket, robot_object)
    )

if __name__ == "__main__":
    asyncio.run(main())
