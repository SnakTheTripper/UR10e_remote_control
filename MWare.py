import asyncio
import sys
import json
import time

import zmq.asyncio
import config
import config_utils
from asyncio.windows_events import WindowsSelectorEventLoopPolicy

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Set then check Update frequency for RTDE & OPCUA
rtde_freq, rtde_per, opcua_freq, opcua_per = config_utils.get_frequencies()
def initialize_zmq_connections(context):
    to_bridge_socket = context.socket(zmq.PUB)
    from_bridge_socket = context.socket(zmq.SUB)
    to_flask_socket = context.socket(zmq.PUB)
    from_flask_socket = context.socket(zmq.SUB)
    to_opcua_socket = context.socket(zmq.PUB)
    from_opcua_socket = context.socket(zmq.SUB)
    try:  # com with UR10e_bridge
        to_bridge_socket.connect(f"tcp://{config.ip_address_bridge}:{config.port_mw_b}")
        from_bridge_socket.connect(f"tcp://{config.ip_address_bridge}:{config.port_b_mw}")
        print('\033[32mUR10e Bridge ports bound!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to UR10e Bridge! {e}\033[0m")

    try:  # com with Flask Server
        to_flask_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_mw_f}")
        from_flask_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_f_mw}")
        print('\033[32mFlask Server ports bound!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to Flask Server! {e}\033[0m")

    try:  # com with OPCUA Server
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
        self.current_joint = [0.0] * 6
        self.target_joint = [0.0] * 6

        self.current_tcp = [0.0] * 6
        self.target_tcp = [0.0] * 6

        # represents last used move_type
        self.move_type = 1  # 0 = linear 1 = joint
        self.joint_speed = 10
        self.joint_accel = 10
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

        self.control_mode = config.default_control_mode  # 0 = flask  1 = opcua

    def update_local_dataset(self, data_dictionary):
        for key, value in data_dictionary.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f'Tried updating {key}, but it not an attribute of the object!')

    def gather_to_send_all(self):  # send all attributes
        return {key: value for key, value in self.__dict__.items() if
                key in ['current_joint',
                        'target_joint',
                        'current_tcp',
                        'target_tcp',
                        'move_type',
                        'joint_speed',
                        'joint_accel',
                        'linear_speed',
                        'linear_accel',
                        'is_moving',
                        'STOP',
                        'input_bit_0',
                        'input_bit_1',
                        'input_bit_2',
                        'input_bit_3',
                        'input_bit_4',
                        'input_bit_5',
                        'input_bit_6',
                        'input_bit_7',
                        'output_bit_0',
                        'output_bit_1',
                        'output_bit_2',
                        'output_bit_3',
                        'output_bit_4',
                        'output_bit_5',
                        'output_bit_6',
                        'output_bit_7',
                        ]}

    def gather_to_send_current(self):  # send all attributes
        return {key: value for key, value in self.__dict__.items() if
                key in ['current_joint',
                        'current_tcp',
                        'is_moving',
                        'STOP']}

class FlaskHandler:
    def __init__(self, to_flask, from_flask, to_bridge, local_ur):
        self.opcua_handler = None
        self.to_flask_sock = to_flask
        self.to_bridge_sock = to_bridge

        self.from_flask_sock = from_flask
        self.from_flask_sock.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
        self.from_flask_sock.setsockopt(zmq.SUBSCRIBE, b"page_init")
        self.from_flask_sock.setsockopt(zmq.SUBSCRIBE, b"switchControl")

        self.local_ur10e = local_ur

    def set_cross_dependency(self, opcua_handler):
        self.opcua_handler = opcua_handler

    async def send(self):
        # send updates to Flask
        last_drops = 10
        while True:
            if last_drops > 0 or self.local_ur10e.page_init:
                serialized_message = None

                if self.local_ur10e.control_mode == 0:
                    serialized_message = json.dumps(self.local_ur10e.gather_to_send_current()).encode()
                elif self.local_ur10e.control_mode == 1:
                    serialized_message = json.dumps(self.local_ur10e.gather_to_send_all()).encode()

                try:
                    await self.to_flask_sock.send_multipart([b"Joint_States", serialized_message])
                except Exception as e:
                    print(f'Can not send update to Flask: {e}')

                if not self.local_ur10e.is_moving:
                    last_drops -= 1  # decrease only when not moving

            if self.local_ur10e.is_moving:
                last_drops = 10

            await asyncio.sleep(rtde_per)

    async def receive(self):
        topic = None
        serialized_message = None

        # receive from Flask
        while True:
                try:
                    topic, serialized_message = await self.from_flask_sock.recv_multipart()
                except Exception as e:
                    print(e)

                if topic == b'Move_Commands':
                    # quickly forward to bridge
                    await self.to_bridge_sock.send_multipart([topic, serialized_message])
                    # then unpack and update local dataset
                    self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                    message = json.loads(serialized_message.decode())
                    print(f'debug: target tcp pose: {message}')

                elif topic == b'page_init':
                    self.local_ur10e.page_init = True
                    await asyncio.sleep(5 * rtde_per)
                    self.local_ur10e.page_init = False

                elif topic == b"switchControl":
                    # set local control_mode value to opcua
                    self.local_ur10e.control_mode = json.loads(serialized_message.decode())
                    print(f'local control_mode set to {self.local_ur10e.control_mode}')

                    # send control_mode update to OPCUA Server
                    await self.opcua_handler.to_opcua_sock.send_multipart([b"switchControl", serialized_message])
                    print(f'control_mode {self.local_ur10e.control_mode} sent to opcua server')

class OpcuaHandler:
    def __init__(self, to_opcua, from_opcua, to_bridge, local_ur):
        self.flask_handler = None
        self.to_opcua_sock = to_opcua
        self.to_bridge_sock = to_bridge

        self.from_opcua_sock = from_opcua
        self.from_opcua_sock.setsockopt(zmq.SUBSCRIBE, b"opcua_command")
        self.from_opcua_sock.setsockopt(zmq.SUBSCRIBE, b"switchControl")

        self.local_ur10e = local_ur

    def set_cross_dependency(self, flask_handler):
        self.flask_handler = flask_handler

    async def send(self):
        # send to OPCUA from MW database
        serialized_message = None
        while True:
            if self.local_ur10e.control_mode == 0:  # flask
                serialized_message = json.dumps(self.local_ur10e.gather_to_send_all()).encode()  # dictionary of robot attributes
            elif self.local_ur10e.control_mode == 1:  # opcua
                serialized_message = json.dumps(self.local_ur10e.gather_to_send_current()).encode()

            await self.to_opcua_sock.send_multipart([b"update_package", serialized_message])
            await asyncio.sleep(opcua_per)

    async def receive(self):  # receive from OPCUA
        topic = None
        serialized_message = None
        while True:
            try:
                topic, serialized_message = await self.from_opcua_sock.recv_multipart()
            except Exception as e:
                print(f'Could not receive message from OPCUA Server: {e}')

            if topic == b'opcua_command':
                # quickly forward to bridge
                await self.to_bridge_sock.send_multipart([topic, serialized_message])
                # then unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
            elif topic == b"switchControl":
                # update local control_mode
                self.local_ur10e.control_mode = json.loads(serialized_message.decode())
                print(f'local control_mode set to {self.local_ur10e.control_mode}')

                # send control_mode update to Flask Server
                await self.flask_handler.to_flask_sock.send_multipart([b"switchControl", serialized_message])
                print(f'control {self.local_ur10e.control_mode} sent to flask server')


async def receive_from_bridge(from_bridge_sock, local_ur10e):
    from_bridge_sock.setsockopt(zmq.SUBSCRIBE, b'Joint_States')
    while True:
        topic, serialized_message = await from_bridge_sock.recv_multipart()
        local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))  # blocking command
async def main():
    local_ur10e = UR10e()

    context = zmq.asyncio.Context()
    (to_opcua_socket,
     to_bridge_socket,
     to_flask_socket,
     from_bridge_socket,
     from_opcua_socket,
     from_flask_socket) = initialize_zmq_connections(context)

    flask_handler = FlaskHandler(to_flask_socket, from_flask_socket, to_bridge_socket, local_ur10e)
    opcua_handler = OpcuaHandler(to_opcua_socket, from_opcua_socket, to_bridge_socket, local_ur10e)

    # set cross dependencies so flask and opcua handlers can use each other's methods
    flask_handler.set_cross_dependency(opcua_handler)
    opcua_handler.set_cross_dependency(flask_handler)

    await asyncio.gather(flask_handler.send(),
                         flask_handler.receive(),
                         opcua_handler.send(),
                         opcua_handler.receive(),
                         receive_from_bridge(from_bridge_socket, local_ur10e))

if __name__ == "__main__":
    asyncio.run(main())
