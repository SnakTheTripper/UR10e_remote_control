import asyncio

# from asyncua import ua, Server
from opcua import ua, Server

# data transfer
import zmq
import json

# locals
import config
import ur10e_object
from datetime import datetime

class UR10e:
    def __init__(self):
        self.current_joint = [0.0] * 6
        self.target_joint = [0.0] * 6

        self.current_tcp = [0.0] * 6
        self.target_tcp = [0.0] * 6

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

    async def update_from_message(self, message):
        for key, value in message.items():
            setattr(self, key, value)

prev_time=datetime.now()

async def freq_calc(message):
    global prev_time
    current_time = datetime.now()
    delta_time = (current_time - prev_time).total_seconds()

    if delta_time > 0:  # Avoid division by zero
        frequency = 1 / delta_time
        print(f"Frequency: {frequency:.2f} Hz - Updated! {message}")

    prev_time = current_time


def initialize_OPCUA_server():
    try:
        server = Server()
        full_path = f"opc.tcp://{config.ip_address_opcua_server}:{config.port_opcua}"
        server.set_endpoint(full_path)

        uri = 'https://UiT-remote-control-project.no'
        addspace = server.register_namespace(uri)
        node = server.get_objects_node()

        # Populate server from ur10e_object.py
        opcua_dataset = ur10e_object.ur10e_platform_variables(addspace, node)

        server.start()
        print('OPCUA Server started!')
        return opcua_dataset

    except Exception as e:
        print(f'Error starting OPCUA Server: {e}')

def initialize_ZMQ_connection():
    while True:
        try:
            context = zmq.Context()
            from_mw = context.socket(zmq.SUB)
            from_mw.connect(f"tcp://{config.ip_address_MW}:{config.port_mw_op}")
            from_mw.setsockopt(zmq.SUBSCRIBE, b"update_package")
            print('ZMQ - Connected to MiddleWare')
            return from_mw
        except Exception as e:
            print(f'Error: {e}\nRetrying connection...')

async def update_OPCUA_values(local_robot_state, opcua_dataset):
    # Update current joint positions
    for i in range(6):
        opcua_dataset[i].set_value(local_robot_state.current_joint[i])

    # Update target joint positions
    for i in range(6, 12):
        opcua_dataset[i].set_value(local_robot_state.target_joint[i - 6])

    # Update current TCP positions
    for i in range(12, 18):
        opcua_dataset[i].set_value(local_robot_state.current_tcp[i - 12])

    # Update target TCP positions
    for i in range(18, 24):
        opcua_dataset[i].set_value(local_robot_state.target_tcp[i - 18])

    # Update Control
    control_start = 25
    opcua_dataset[control_start].set_value(local_robot_state.move_type)
    opcua_dataset[control_start + 1].set_value(local_robot_state.joint_speed)
    opcua_dataset[control_start + 2].set_value(local_robot_state.joint_accel)
    opcua_dataset[control_start + 3].set_value(local_robot_state.linear_speed)
    opcua_dataset[control_start + 4].set_value(local_robot_state.linear_accel)
    opcua_dataset[control_start + 5].set_value(local_robot_state.is_moving)

    # Update Digital Inputs
    digital_inputs_start = 31
    for i in range(8):
        opcua_dataset[digital_inputs_start + i].set_value(getattr(local_robot_state, f'input_bit_{i}'))

    # Update Digital Outputs
    digital_outputs_start = 39
    for i in range(8):
        opcua_dataset[digital_outputs_start + i].set_value(getattr(local_robot_state, f'output_bit_{i}'))

async def listen_to_mw(local_robot_state):
    from_mw_socket = initialize_ZMQ_connection()
    opcua_dataset = initialize_OPCUA_server()
    while True:
        [topic, message_raw] = from_mw_socket.recv_multipart()
        message = json.loads(message_raw.decode())
        await freq_calc(message)
        await local_robot_state.update_from_message(message)    # message needs to be a dictionary
        await update_OPCUA_values(local_robot_state, opcua_dataset)

async def main():
    local_robot_state = UR10e()
    await asyncio.create_task(listen_to_mw(local_robot_state))  # Start listening to MW

if __name__ == "__main__":
    asyncio.run(main())
