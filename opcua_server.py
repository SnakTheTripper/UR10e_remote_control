import asyncio
import sys

import zmq.asyncio

# from asyncua import ua, Server
from opcua import Server

# data transfer
import zmq
import json

# locals
import config
import project_utils as pu
import ur10e_object
from datetime import datetime

# disable when running on Linux based systems
from asyncio.windows_events import WindowsSelectorEventLoopPolicy
asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Set then check Update frequency for OPCUA
freq_dict = pu.get_frequencies()
opcua_per = freq_dict['opcua_per']

prev_time = datetime.now()

async def freq_calc():
    global prev_time
    current_time = datetime.now()
    delta_time = (current_time - prev_time).total_seconds()

    if delta_time > 0:  # Avoid division by zero
        frequency = 1 / delta_time
        print(f"Update Frequency: {frequency:.2f} Hz")

    prev_time = current_time


def initialize_OPCUA_server():
    try:
        server = Server()
        full_path = f"opc.tcp://{config.IP_OPCUA}:{config.PORT_OPCUA}"
        server.set_endpoint(full_path)

        uri = 'https://UiT-remote-control-project.no'
        addspace = server.register_namespace(uri)
        node = server.get_objects_node()

        # Populate server from ur10e_object.py
        try:
            opcua_dataset = ur10e_object.ur10e_platform_variables(addspace, node)
        except Exception as e:
            sys.exit(f'Error bari: {e}')

        server.start()
        print('OPCUA Server started!')
        return opcua_dataset

    except Exception as e:
        print(f'Error starting OPCUA Server: {e}')


def initialize_ZMQ_connection():
    while True:
        try:
            context = zmq.asyncio.Context()
            from_mw = context.socket(zmq.SUB)
            to_mw = context.socket(zmq.PUB)

            from_mw.connect(f"tcp://{config.IP_MWARE}:{config.PORT_MW_OP}")
            to_mw.connect(f"tcp://{config.IP_MWARE}:{config.PORT_OP_MW}")

            from_mw.setsockopt(zmq.SUBSCRIBE, b"update_package")
            from_mw.setsockopt(zmq.SUBSCRIBE, b"switchControl")

            print('ZMQ - Connected to MiddleWare')
            return from_mw, to_mw
        except Exception as e:
            print(f'Error: {e}\nRetrying connection...')


class UR10e:
    def __init__(self):
        self.current_joint = [0.0] * 6
        self.target_joint = [0.0] * 6

        self.current_tcp = [0.0] * 6
        self.target_tcp = [0.0] * 6

        # represents last used move_type
        self.move_type = 1  # 0 = linear 1 = joint
        self.control_mode = config.DEFAULT_MODE  # 0 = flask  1 = opcua
        self.joint_speed = 0.1
        self.joint_accel = 0.1
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

        self.SEND_MOVEMENT = 0
        self.SEND_OUTPUT_BITS = 0

    def update_local_from_mw(self, message):
        for key, value in message.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                print(f'Tried updating {key}, but it not an attribute of the object!')

    def gather_to_send_command_values(self):
        return {'target_joint': self.target_joint,
                'target_tcp': self.target_tcp,
                'move_type': self.move_type,
                'joint_speed': self.joint_speed,
                'joint_accel': self.joint_accel,
                'linear_speed': self.linear_speed,
                'linear_accel': self.linear_accel,
                'STOP': self.STOP}

    def gather_to_send_output_bits(self):
        return {'target_standard_output_bits': self.target_standard_output_bits,
                'target_configurable_output_bits': self.target_configurable_output_bits,
                'target_tool_output_bits': self.target_tool_output_bits}


class OpcuaValueHandler:
    def __init__(self, opcua_dataset, local_ur):
        self.opcua_dataset = opcua_dataset
        self.local_ur10e = local_ur
        self.browse_name_to_var = {
            "Current Base": self.opcua_dataset[0],
            "Current Shoulder": self.opcua_dataset[1],
            "Current Elbow": self.opcua_dataset[2],
            "Current Wrist 1": self.opcua_dataset[3],
            "Current Wrist 2": self.opcua_dataset[4],
            "Current Wrist 3": self.opcua_dataset[5],

            "Target Base": self.opcua_dataset[6],
            "Target Shoulder": self.opcua_dataset[7],
            "Target Elbow": self.opcua_dataset[8],
            "Target Wrist 1": self.opcua_dataset[9],
            "Target Wrist 2": self.opcua_dataset[10],
            "Target Wrist 3": self.opcua_dataset[11],

            "Current x": self.opcua_dataset[12],
            "Current y": self.opcua_dataset[13],
            "Current z": self.opcua_dataset[14],
            "Current Roll": self.opcua_dataset[15],
            "Current Pitch": self.opcua_dataset[16],
            "Current Yaw": self.opcua_dataset[17],

            "Target x": self.opcua_dataset[18],
            "Target y": self.opcua_dataset[19],
            "Target z": self.opcua_dataset[20],
            "Target Roll": self.opcua_dataset[21],
            "Target Pitch": self.opcua_dataset[22],
            "Target Yaw": self.opcua_dataset[23],

            "move_type": self.opcua_dataset[24],
            "control_mode": self.opcua_dataset[25],
            "Joint Speed": self.opcua_dataset[26],
            "Joint Acceleration": self.opcua_dataset[27],
            "TCP Speed": self.opcua_dataset[28],
            "TCP Acceleration": self.opcua_dataset[29],
            "is_moving": self.opcua_dataset[30],

            "standard_input_bits": self.opcua_dataset[31],
            "configurable_input_bits": self.opcua_dataset[32],
            "tool_input_bits": self.opcua_dataset[33],

            "standard_output_bits": self.opcua_dataset[34],
            "configurable_output_bits": self.opcua_dataset[35],
            "tool_output_bits": self.opcua_dataset[36],

            "target_standard_output_bits": self.opcua_dataset[37],
            "target_configurable_output_bits": self.opcua_dataset[38],
            "target_tool_output_bits": self.opcua_dataset[39],

            "SEND MOVEMENT": self.opcua_dataset[40],
            "SEND OUTPUT BITS": self.opcua_dataset[41],
            "STOP": self.opcua_dataset[42]
        }

    def update_opcua_from_local(self):
        # only update targets on opcua server when flask is in control
        if self.local_ur10e.control_mode == 0:      # Flask
            # Updating target joint and TCP positions only when not in 'opcua' control_mode
            browse_names_target_joint = ["Target Base", "Target Shoulder", "Target Elbow", "Target Wrist 1",
                                         "Target Wrist 2", "Target Wrist 3"]
            browse_names_target_tcp = ["Target x", "Target y", "Target z", "Target Roll", "Target Pitch", "Target Yaw"]

            for i, name in enumerate(browse_names_target_joint):
                self.browse_name_to_var[name].set_value(self.local_ur10e.target_joint[i])

            for i, name in enumerate(browse_names_target_tcp):
                self.browse_name_to_var[name].set_value(self.local_ur10e.target_tcp[i])

            # set control variable values

            control_start = 24
            self.opcua_dataset[control_start].set_value(self.local_ur10e.move_type)
            # not updating control_mode, that value is changed separately for switchability
            self.opcua_dataset[control_start + 2].set_value(self.local_ur10e.joint_speed)
            self.opcua_dataset[control_start + 3].set_value(self.local_ur10e.joint_accel)
            self.opcua_dataset[control_start + 4].set_value(self.local_ur10e.linear_speed)
            self.opcua_dataset[control_start + 5].set_value(self.local_ur10e.linear_accel)
            self.opcua_dataset[control_start + 6].set_value(self.local_ur10e.is_moving)

        # Updating current joint and TCP positions
        browse_names_current_joint = ["Current Base", "Current Shoulder", "Current Elbow", "Current Wrist 1",
                                      "Current Wrist 2", "Current Wrist 3"]
        browse_names_current_tcp = ["Current x", "Current y", "Current z", "Current Roll", "Current Pitch", "Current Yaw"]

        for i, name in enumerate(browse_names_current_joint):
            self.browse_name_to_var[name].set_value(self.local_ur10e.current_joint[i])

        for i, name in enumerate(browse_names_current_tcp):
            self.browse_name_to_var[name].set_value(self.local_ur10e.current_tcp[i])

        # Update Digital Inputs
        for i in range(8):
            self.browse_name_to_var['standard_input_bits'][i].set_value(self.local_ur10e.standard_input_bits[i])
            self.browse_name_to_var['configurable_input_bits'][i].set_value(self.local_ur10e.configurable_input_bits[i])
        for i in range(2):
            self.browse_name_to_var['tool_input_bits'][i].set_value(self.local_ur10e.tool_input_bits[i])

        # Update Digital Outputs
        for i in range(8):
            self.browse_name_to_var['standard_output_bits'][i].set_value(self.local_ur10e.standard_output_bits[i])
            self.browse_name_to_var['configurable_output_bits'][i].set_value(self.local_ur10e.configurable_output_bits[i])

        for i in range(2):
            self.browse_name_to_var['tool_output_bits'][i].set_value(self.local_ur10e.tool_output_bits[i])

        if self.local_ur10e.control_mode == 0:      # Flask
            # Updating Target Digital Outputs only when not in 'opcua' control_mode
            for i in range(8):
                self.browse_name_to_var['target_standard_output_bits'][i].set_value(self.local_ur10e.target_standard_output_bits[i])
                self.browse_name_to_var['target_configurable_output_bits'][i].set_value(self.local_ur10e.target_configurable_output_bits[i])
            for i in range(2):
                self.browse_name_to_var['target_tool_output_bits'][i].set_value(self.local_ur10e.target_tool_output_bits[i])

    def update_local_from_opcua(self):
        browse_names_target_joint = ["Target Base", "Target Shoulder", "Target Elbow", "Target Wrist 1",
                                     "Target Wrist 2", "Target Wrist 3"]
        browse_names_target_tcp = ["Target x", "Target y", "Target z", "Target Roll", "Target Pitch", "Target Yaw"]

        for i, name in enumerate(browse_names_target_joint):
            self.local_ur10e.target_joint[i] = self.browse_name_to_var[name].get_value()

        for i, name in enumerate(browse_names_target_tcp):
            self.local_ur10e.target_tcp[i] = self.browse_name_to_var[name].get_value()

        # Update Control
        self.local_ur10e.move_type = self.browse_name_to_var["move_type"].get_value()
        self.local_ur10e.control_mode = self.browse_name_to_var["control_mode"].get_value()
        self.local_ur10e.joint_speed = self.browse_name_to_var["Joint Speed"].get_value()
        self.local_ur10e.joint_accel = self.browse_name_to_var["Joint Acceleration"].get_value()
        self.local_ur10e.linear_speed = self.browse_name_to_var["TCP Speed"].get_value()
        self.local_ur10e.linear_accel = self.browse_name_to_var["TCP Acceleration"].get_value()
        self.local_ur10e.is_moving = self.browse_name_to_var["is_moving"].get_value()
        self.local_ur10e.STOP = self.browse_name_to_var["STOP"].get_value()

        # Update Target Digital Outputs
        for i in range(8):
            self.local_ur10e.target_standard_output_bits[i] = self.browse_name_to_var['target_standard_output_bits'][i].get_value()

        for i in range(8):
            self.local_ur10e.target_configurable_output_bits[i] = self.browse_name_to_var['target_configurable_output_bits'][i].get_value()

        for i in range(2):
            self.local_ur10e.target_tool_output_bits[i] = self.browse_name_to_var['target_tool_output_bits'][i].get_value()

        self.local_ur10e.SEND_MOVEMENT = self.browse_name_to_var["SEND MOVEMENT"].get_value()
        self.local_ur10e.SEND_OUTPUT_BITS = self.browse_name_to_var["SEND OUTPUT BITS"].get_value()

    def reset_send_movement_flag(self):
        self.browse_name_to_var["SEND MOVEMENT"].set_value(self.local_ur10e.SEND_MOVEMENT)

    def reset_send_output_bit_flag(self):
        self.browse_name_to_var["SEND OUTPUT BITS"].set_value(self.local_ur10e.SEND_OUTPUT_BITS)

    def reset_stop_flag(self):
        self.browse_name_to_var["STOP"].set_value(self.local_ur10e.STOP)


class MiddlewareHandler:
    def __init__(self, from_mw, to_mw, opcua_dataset, local_ur, opcua_value_handler):
        self.from_mw_sock = from_mw
        self.to_mw_sock = to_mw
        self.opcua_dataset = opcua_dataset
        self.local_ur10e = local_ur
        self.opcua_value_handler = opcua_value_handler

        self.init_done = False

    async def send_movement(self):
        message = self.local_ur10e.gather_to_send_command_values()
        serialized_message = json.dumps(message).encode()
        await self.to_mw_sock.send_multipart([b"Move_Command", serialized_message])

    async def send_output_bits(self):
        message = self.local_ur10e.gather_to_send_output_bits()
        serialized_message = json.dumps(message).encode()
        await self.to_mw_sock.send_multipart([b"output_bit_command", serialized_message])

    async def receive_from_mw(self):
        topic = None
        message = None
        while True:
            try:
                [topic, message_raw] = await self.from_mw_sock.recv_multipart()
                message = json.loads(message_raw.decode())
            except Exception as e:
                print(e)
            if topic == b"update_package":
                # await freq_calc()
                self.local_ur10e.update_local_from_mw(message)  # message needs to be a dictionary
                self.opcua_value_handler.update_opcua_from_local()
                # no need to sleep as .recv_multipart() is awaited and it will block this function

            elif topic == b"switchControl":
                # update local control_mode value
                self.local_ur10e.control_mode = message
                # update control_mode opcua node value
                self.opcua_value_handler.browse_name_to_var["control_mode"].set_value(self.local_ur10e.control_mode)

                print(f'control_mode set by FLASK to: {self.local_ur10e.control_mode}')

    async def send_to_mw(self):
        while True:
            # to check if control_mode has been modified by opcua client
            old_control_mode = self.local_ur10e.control_mode
            self.opcua_value_handler.update_local_from_opcua()
            new_control_mode = self.local_ur10e.control_mode

            # this will only run if the control_mode has been changed from opcua client side
            if new_control_mode != old_control_mode:
                await self.to_mw_sock.send_multipart([b"switchControl", json.dumps(new_control_mode).encode()])
                print(f"Sent new control_mode to MW: {new_control_mode}")

            if self.local_ur10e.control_mode == 1:  # opcua

                if self.local_ur10e.STOP == 1:
                    await self.send_movement()

                    while self.local_ur10e.reset_STOP_flag == 0:
                        print('debug: waiting for reset_STOP_flag from MW')
                        await asyncio.sleep(opcua_per)  # get stuck here until reset_STOP_flag arrives from bridge

                    self.local_ur10e.STOP = 0  # reset STOP when reset_STOP_flag arrives
                    self.opcua_value_handler.reset_stop_flag()
                    print('debug: sending the reset STOP = 0 value')
                    await self.send_movement()  # send again bc STOP has been reset

                elif self.local_ur10e.SEND_MOVEMENT == 1:
                    await self.send_movement()

                    self.local_ur10e.SEND_MOVEMENT = 0  # reset send flag so it acts like a button
                    self.opcua_value_handler.reset_send_movement_flag()

                elif self.local_ur10e.SEND_OUTPUT_BITS == 1:
                    await self.send_output_bits()

                    self.local_ur10e.SEND_OUTPUT_BITS = 0   # reset value so it acts like a button
                    self.opcua_value_handler.reset_send_output_bit_flag()

            await asyncio.sleep(opcua_per)  # wait OPCUA period


async def main():
    local_ur10e = UR10e()
    opcua_dataset = initialize_OPCUA_server()

    from_mw_socket, to_mw_socket = initialize_ZMQ_connection()

    opcua_value_handler = OpcuaValueHandler(opcua_dataset, local_ur10e)
    middleware_handler = MiddlewareHandler(from_mw_socket, to_mw_socket, opcua_dataset, local_ur10e,
                                           opcua_value_handler)

    await asyncio.gather(middleware_handler.receive_from_mw(),
                         middleware_handler.send_to_mw())


if __name__ == "__main__":
    asyncio.run(main())
