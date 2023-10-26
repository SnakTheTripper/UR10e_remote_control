import asyncio
import sys
import json
import time

import zmq.asyncio
import config
import project_utils as pu

# disable when running on Linux based systems
from asyncio.windows_events import WindowsSelectorEventLoopPolicy

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Set then check Update frequency for Flask and OPCUA
freq_dict = pu.get_frequencies()
flask_per = freq_dict['flask_per']
opcua_per = freq_dict['opcua_per']


def initialize_zmq_connections(context):
    to_bridge_socket = context.socket(zmq.PUB)
    from_bridge_socket = context.socket(zmq.SUB)
    flask_polling = context.socket(zmq.REQ)
    to_flask_update = context.socket(zmq.PUB)
    to_opcua_socket = context.socket(zmq.PUB)
    from_opcua_socket = context.socket(zmq.SUB)
    try:  # com with UR10e_bridge
        to_bridge_socket.connect(f"tcp://{config.IP_BRIDGE}:{config.PORT_MW_B}")
        from_bridge_socket.connect(f"tcp://{config.IP_BRIDGE}:{config.PORT_B_MW}")
        print('\033[32mUR10e Bridge ports bound!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to UR10e Bridge! {e}\033[0m")

    try:  # com with Flask Server
        if config.ONLINE_MODE:
            flask_polling.connect(f"tcp://{config.IP_FLASK_CLOUD}:{config.PORT_FLASK_POLL}")
            to_flask_update.connect(f"tcp://{config.IP_FLASK_CLOUD}:{config.PORT_FLASK_UPDATE}")
        else:
            flask_polling.connect(f"tcp://{config.IP_FLASK_LOCAL}:{config.PORT_FLASK_POLL}")
            to_flask_update.connect(f"tcp://{config.IP_FLASK_LOCAL}:{config.PORT_FLASK_UPDATE}")
        print(f'\033[32mConnected to Flask Dummy on {config.IP_FLASK_LOCAL}!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to Flask Server! {e}\033[0m")

    try:  # com with OPCUA Server
        to_opcua_socket.bind(f"tcp://{config.IP_MWARE}:{config.PORT_MW_OP}")
        from_opcua_socket.bind(f"tcp://{config.IP_MWARE}:{config.PORT_OP_MW}")
        print('\033[32mOPCUA Server ports bound!\033[0m')
    except Exception as e:
        sys.exit(f"\033[91mCan't connect to OPCUA Server! {e}\033[0m")

    print(
        f'Publish on port: {config.PORT_FLASK_POLL} & {config.PORT_MW_B} & {config.PORT_OP_MW}\n'
        f'Listening on port: {str(8090)} & {config.PORT_B_MW} & {config.PORT_MW_OP}')

    return to_opcua_socket, to_bridge_socket, flask_polling, to_flask_update, from_bridge_socket, from_opcua_socket


class UR10e:
    def __init__(self):
        self.current_joint = [0.0] * 6
        self.target_joint = [0.0] * 6

        self.current_tcp = [0.0] * 6
        self.target_tcp = [0.0] * 6

        self.move_type = 1  # 0 = linear 1 = joint (represents last used move_type)
        self.control_mode = config.DEFAULT_MODE  # 0 = flask  1 = opcua

        self.joint_speed = 10
        self.joint_accel = 10
        self.linear_speed = 0.1
        self.linear_accel = 0.1
        self.is_moving = 0
        self.STOP = 0
        self.reset_STOP_flag = 0

        # current digital inputs
        self.standard_input_bits = [0] * 8
        self.configurable_input_bits = [0] * 8
        self.tool_input_bits = [0] * 2

        # current digital outputs
        self.standard_output_bits = [0] * 8
        self.configurable_output_bits = [0] * 8
        self.tool_output_bits = [0] * 2

        # target digital outputs
        self.target_standard_output_bits = [0] * 8
        self.target_configurable_output_bits = [0] * 8
        self.target_tool_output_bits = [0] * 2

        self.page_init = False

    def update_local_dataset(self, data_dictionary):
        for key, value in data_dictionary.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f'Tried updating {key}, but it not an attribute of the object!')

    def gather_to_send_all(self):  # send all attributes (incl. target) to inactive controller
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

                        'standard_input_bits',
                        'configurable_input_bits',
                        'tool_input_bits',

                        'standard_output_bits',
                        'configurable_output_bits',
                        'tool_output_bits',

                        'target_standard_output_bits',
                        'target_configurable_output_bits',
                        'target_tool_output_bits'
                        ]}

    def gather_to_send_current(self):  # send status updates to active controller
        return {key: value for key, value in self.__dict__.items() if
                key in ['current_joint',
                        'current_tcp',
                        'is_moving',
                        'reset_STOP_flag',

                        'standard_input_bits',
                        'configurable_input_bits',
                        'tool_input_bits',

                        'standard_output_bits',
                        'configurable_output_bits',
                        'tool_output_bits'
                        ]}  # add input bits when added to bridge


class FlaskHandler:
    def __init__(self, flask_polling, to_flask_update, to_bridge, local_ur):
        self.opcua_handler = None
        self.flask_polling = flask_polling
        self.to_flask_update = to_flask_update
        self.to_bridge_sock = to_bridge

        # discard old REQs if a new one is sent out
        self.flask_polling.setsockopt(zmq.REQ_RELAXED, 1)

        self.local_ur10e = local_ur

        self.standby_period = 1  # for frequency of 1 Hz
        self.flask_period = flask_per  # by default coming from project_utils.py

        # period between checking if standby or rtde period should be used in sending current states to Flask
        self.calculate_flask_frequency_period = 0.1

        self.polling_reply_detected = False

    def set_cross_dependency(self, opcua_handler):
        self.opcua_handler = opcua_handler

    async def polling_mechanism(self):
        while True:
            self.polling_reply_detected = False
            try:
                self.flask_polling.send(b'poll')
            except zmq.ZMQError as e:
                print(f"ZMQ Error: {e}")

            timeout_counter = 0  # Initialize timeout counter
            while not self.polling_reply_detected:
                await asyncio.sleep(flask_per)

                timeout_counter += flask_per  # Increment counter

                if timeout_counter >= 1.0:  # If 1 second has passed
                    print("Timeout reached, sending another poll.")
                    try:
                        # Reconnect logic
                        if config.ONLINE_MODE:
                            self.flask_polling.connect(f"tcp://{config.IP_FLASK_CLOUD}:{config.PORT_FLASK_POLL}")
                        else:
                            self.flask_polling.connect(f"tcp://{config.IP_FLASK_LOCAL}:{config.PORT_FLASK_POLL}")
                    except Exception as e:
                        print(f"Exception while resetting socket: {e}")
                    break  # Exit the inner loop

    async def send(self):
        # send updates to Flask
        while True:
            serialized_message = None

            if self.local_ur10e.control_mode == 0:  # flask
                serialized_message = json.dumps(self.local_ur10e.gather_to_send_current()).encode()
            elif self.local_ur10e.control_mode == 1:  # opcua
                serialized_message = json.dumps(self.local_ur10e.gather_to_send_all()).encode()

            try:
                await self.to_flask_update.send_multipart([b"Joint_States", serialized_message])
            except Exception as e:
                print(f'Can not send update to Flask: {e}')

            await asyncio.sleep(self.flask_period)

    async def receive(self):
        topic = None
        serialized_message = None

        # receive from Flask
        while True:
            try:
                topic, serialized_message = await self.flask_polling.recv_multipart()
                self.polling_reply_detected = True
            except Exception as e:
                print(e)

            if topic == b'Move_Command':
                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                message = json.loads(serialized_message.decode())
                print(f'debug: target tcp pose: {message}')
                # forward to bridge
                await self.to_bridge_sock.send_multipart([topic, serialized_message])
                print(f'debug: sent to bridge, STOP =  {self.local_ur10e.STOP}')

            elif topic == b'output_bit_command':
                print('debug: output_bit_command arrived!')
                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                # forward to bridge
                await self.to_bridge_sock.send_multipart([topic, serialized_message])

            elif topic == b"switchControl":
                # set local control_mode value to opcua
                self.local_ur10e.control_mode = json.loads(serialized_message.decode())
                print(f'local control_mode set to {self.local_ur10e.control_mode}')

                # send control_mode update to OPCUA Server
                await self.opcua_handler.to_opcua_sock.send_multipart([b"switchControl", serialized_message])
                print(f'control_mode {self.local_ur10e.control_mode} sent to opcua server')

    async def calculate_flask_frequency(self):
        while True:
            if self.local_ur10e.is_moving or self.local_ur10e.STOP:
                self.flask_period = flask_per
            else:
                self.flask_period = self.standby_period

            # print(f'flask period: {self.flask_period}')
            await asyncio.sleep(self.calculate_flask_frequency_period)


class OpcuaHandler:
    def __init__(self, to_opcua, from_opcua, to_bridge, local_ur):
        self.flask_handler = None
        self.to_opcua_sock = to_opcua
        self.to_bridge_sock = to_bridge

        self.from_opcua_sock = from_opcua
        self.from_opcua_sock.setsockopt(zmq.SUBSCRIBE, b"Move_Command")
        self.from_opcua_sock.setsockopt(zmq.SUBSCRIBE, b"output_bit_command")
        self.from_opcua_sock.setsockopt(zmq.SUBSCRIBE, b"switchControl")

        self.local_ur10e = local_ur

    def set_cross_dependency(self, flask_handler):
        self.flask_handler = flask_handler

    async def send(self):
        # send to OPCUA from MW database
        serialized_message = None
        while True:
            if self.local_ur10e.control_mode == 0:  # flask
                serialized_message = json.dumps(
                    self.local_ur10e.gather_to_send_all()).encode()  # dictionary of robot attributes
            elif self.local_ur10e.control_mode == 1:  # opcua
                serialized_message = json.dumps(self.local_ur10e.gather_to_send_current()).encode()

            try:
                await self.to_opcua_sock.send_multipart([b"update_package", serialized_message])
            except Exception as e:
                print(f'Can not send update to OPCUA: {e}')
            await asyncio.sleep(opcua_per)

    async def receive(self):  # receive from OPCUA
        topic = None
        serialized_message = None
        while True:
            try:
                topic, serialized_message = await self.from_opcua_sock.recv_multipart()
            except Exception as e:
                print(f'Could not receive message from OPCUA Server: {e}')

            if topic == b'Move_Command':
                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                # forward to bridge
                await self.to_bridge_sock.send_multipart([topic, serialized_message])

            elif topic == b"output_bit_command":
                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                # forward to bridge
                await self.to_bridge_sock.send_multipart([topic, serialized_message])

            elif topic == b"switchControl":
                # update local control_mode
                self.local_ur10e.control_mode = json.loads(serialized_message.decode())
                print(f'local control_mode set to {self.local_ur10e.control_mode}')

                # send control_mode update to Flask Server
                await self.flask_handler.to_flask_update.send_multipart([b"switchControl", serialized_message])
                print(f'control {self.local_ur10e.control_mode} sent to flask server')


async def receive_from_bridge(from_bridge_sock, local_ur10e):
    from_bridge_sock.setsockopt(zmq.SUBSCRIBE, b'Joint_States')
    while True:
        topic, serialized_message = await from_bridge_sock.recv_multipart()
        local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))  # blocking command

context = zmq.asyncio.Context()

async def main():
    local_ur10e = UR10e()

    (to_opcua_socket,
     to_bridge_socket,
     flask_polling,
     to_flask_update,
     from_bridge_socket,
     from_opcua_socket) = initialize_zmq_connections(context)

    flask_handler = FlaskHandler(flask_polling, to_flask_update, to_bridge_socket, local_ur10e)
    opcua_handler = OpcuaHandler(to_opcua_socket, from_opcua_socket, to_bridge_socket, local_ur10e)

    # set cross dependencies so flask and opcua handlers can use each other's methods
    flask_handler.set_cross_dependency(opcua_handler)
    opcua_handler.set_cross_dependency(flask_handler)

    await asyncio.gather(flask_handler.polling_mechanism(),
                         flask_handler.send(),
                         flask_handler.receive(),
                         flask_handler.calculate_flask_frequency(),
                         opcua_handler.send(),
                         opcua_handler.receive(),
                         receive_from_bridge(from_bridge_socket, local_ur10e))


if __name__ == "__main__":
    asyncio.run(main())
