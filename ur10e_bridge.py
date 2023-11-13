import math
import time
import asyncio
import json
import sys

import rtde_control
import rtde_receive
import rtde_io
import dashboard_client
import zmq.asyncio
import config
import project_utils as pu

# disable when running on Linux based systems
from asyncio.windows_events import WindowsSelectorEventLoopPolicy

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Set then check Update frequency for RTDE
freq_dict = pu.get_frequencies()
rtde_freq = freq_dict['rtde_freq']
rtde_per = freq_dict['rtde_per']


class ZmqHandler:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.sub_socket = None
        self.pub_socket = None

    def connect(self):  # connects to MiddleWare
        print("Binding ZMQ ports...")
        try:
            self.sub_socket = self.context.socket(zmq.SUB)
            self.sub_socket.bind(f"tcp://{config.IP_BRIDGE}:{config.PORT_MW_B}")
            self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"Move_Command")
            self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"output_bit_command")
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://{config.IP_BRIDGE}:{config.PORT_B_MW}")
        except Exception as e:
            sys.exit(f"Can't bind ZMQ Ports: {e}")
        print("ZMQ Connected Successfully\n")

        return self.sub_socket, self.pub_socket


class RtdeHandler:
    def __init__(self):
        self.rtde_r = None
        self.rtde_c = None
        self.rtde_io = None
        self.ur_dashboard_client = dashboard_client.DashboardClient(config.IP_UR10e, 29999)

    def connect_rtde_r(self):
        print("Connecting RTDE Receive Interface...")
        try:
            self.rtde_r = rtde_receive.RTDEReceiveInterface(config.IP_UR10e, frequency=rtde_freq, variables=[])
        except RuntimeError as e:
            print(f"Make sure the robot is powered on!\nError: {e}")
            sys.exit('Start Robot!')

        print("Connected to UR10e Successfully - RTDE Receive\n")
        return self.rtde_r

    def connect_rtde_c(self):

        # Initial Connection

        if self.rtde_c is None:
            print("Connecting RTDE Control Interface...")
            try:
                self.rtde_c = rtde_control.RTDEControlInterface(config.IP_UR10e, frequency=rtde_freq, flags=1)
                print("Connected to UR10e Successfully - RTDE Control\n")
            except RuntimeError as e:
                print(f"Make sure the robot is powered on!\nError: {e}")
                sys.exit('Start Robot!')

        # Reinitialization after Protective stop!

        else:
            print('RTDE Control Reinitializing...')
            try:
                self.rtde_c.disconnect()
                time.sleep(1)
                self.rtde_c.reconnect()
                print('RTDE Control Reinitialized successfully!')
            except Exception as e:
                print(f'Could not reconnect RTDE Control, trying again...')
                self.connect_rtde_c()  # call recursively

        return self.rtde_c

    def connect_rtde_io(self):

        # Initial Connection

        if self.rtde_io is None:
            print("Connecting RTDE I/O Interface...")
            try:
                self.rtde_io = rtde_io.RTDEIOInterface(config.IP_UR10e)
            except RuntimeError as e:
                print(f"Make sure the robot is powered on!\nError: {e}")
                sys.exit('Start Robot!')

            print("Connected to UR10e Successfully - RTDE I/O\n")

        else:
            print('RTDE I/O Reinitializing...')
            try:
                self.rtde_io.disconnect()
                time.sleep(1)
                self.rtde_io.reconnect()
                print('RTDE I/O Reinitialized Successfully!')
            except Exception as e:
                print(f'Could not reconnect RTDE I/O, trying again...')
                self.connect_rtde_io()  # call recursively

        return self.rtde_io

    def connect_ur_dashboard(self):  # RTDEScriptClient API
        print('Connecting UR Dashboard Client...')
        try:
            self.ur_dashboard_client.connect()

        except Exception as e:
            print(f"Make sure the robot is powered on!\nError: {e}")
            sys.exit('Start Robot!')

        print("Connected to UR10e Successfully - Dashboard Client\n")
        return self.ur_dashboard_client

    def connect(self):
        rtde_r = self.connect_rtde_r()
        rtde_c = self.connect_rtde_c()
        rtde_IO = self.connect_rtde_io()
        ur_dashboard_socket = self.connect_ur_dashboard()

        return rtde_r, rtde_c, rtde_IO, ur_dashboard_socket


class UR10e:
    def __init__(self, rtde_r, rtde_c):
        self.rtde_r = rtde_r
        self.rtde_c = rtde_c

        self.current_joint = [0.0] * 6
        self.target_joint = [0.0] * 6

        self.current_tcp = [0.0] * 6
        self.target_tcp = [0.0] * 6

        # represents last used move_type
        self.move_type = 1  # 0 = linear 1 = joint
        self.joint_speed = 0.1
        self.joint_accel = 0.1
        self.joint_accel = 0.1
        self.linear_speed = 0.1
        self.linear_accel = 0.1
        self.is_moving = False
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

    async def get_actual_from_robot(self):
        try:
            self.current_joint = pu.round_array(pu.array_r2d(6, self.rtde_r.getActualQ()), 2)
            self.current_tcp = pu.round_array(pu.m2mm(pu.rv2rpy(self.rtde_r.getActualTCPPose())), 2)

            digital_inputs = self.rtde_r.getActualDigitalInputBits()
            digital_outputs = self.rtde_r.getActualDigitalOutputBits()

            # 0-7: Standard, 8-15: Configurable, 16-17: Tool
            input_binary_string = bin(digital_inputs)[2:].zfill(18)  # 18 bits for UR e-Series
            output_binary_string = bin(digital_outputs)[2:].zfill(18)  # 18 bits for UR e-Series

            input_binary_list = [int(bit) for bit in input_binary_string[::-1]]
            output_binary_list = [int(bit) for bit in output_binary_string[::-1]]

            # Standard
            self.standard_input_bits = input_binary_list[0:8]
            self.standard_output_bits = output_binary_list[0:8]

            # Configurable
            self.configurable_input_bits = input_binary_list[8:16]
            self.configurable_output_bits = output_binary_list[8:16]

            # Tool
            self.tool_input_bits = input_binary_list[16:18]
            self.tool_output_bits = output_binary_list[16:18]

        except Exception as e:
            print(f'Exception in get_actual_from_robot(): {e}')

        if any(element != 0 for element in self.rtde_r.getActualQd()):
            self.is_moving = True
        else:
            self.is_moving = False

    def update_local_dataset(self, data_dictionary):
        for key, value in data_dictionary.items():
            if key not in ['current_joint', 'current_tcp']:
                try:
                    setattr(self, key, value)
                except Exception as e:
                    print(f'Tried updating: {key} to value: {value} but failed\n'
                          f'Exception: {e}')

    def gather_to_send(self):  # excludes unnecessary attributes
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
                        ]}  # needs to send this to reset the STOP variable in MW


class AsyncHandler:
    def __init__(self, zmq_hndlr, rtde_hndlr):
        self.zmq_handler = zmq_hndlr
        self.rtde_handler = rtde_hndlr
        self.local_ur10e = UR10e(rtde_hndlr.rtde_r, rtde_hndlr.rtde_c)
        self.start_movement_flag = False
        self.is_stopped = False
        self.start_setting_output_bits = False

    async def check_status(self):
        check_interval = 1  # seconds
        while True:
            if self.rtde_handler.rtde_c and not self.rtde_handler.rtde_c.isConnected():
                self.rtde_handler.rtde_c.reconnect()

            status_bit = self.rtde_handler.rtde_r.getSafetyMode()

            if status_bit != 1:  # not Normal Mode
                print("STOP DETECTED!")

            while status_bit != 1:
                # Protective Stop
                if status_bit == 3:
                    while status_bit != 1:
                        status_bit = self.rtde_handler.rtde_r.getSafetyMode()
                        await asyncio.sleep(0.1)

                    print("Protective Stop Reset!")
                    self.rtde_handler.connect_rtde_c()
                    # try:
                    #     print('Protective Stop detected. Attempting to clear in 5 seconds...')
                    #     self.rtde_handler.ur_dashboard_client.closeSafetyPopup()
                    #     await asyncio.sleep(0.5)
                    #     self.rtde_handler.ur_dashboard_client.popup('Clearing Protective Stop in 5 seconds...')
                    #
                    #     # wait 5 seconds before clearing Protective Stop
                    #     for i in range(5):
                    #         print(5 - i)
                    #         await asyncio.sleep(1)
                    #
                    #     self.rtde_handler.ur_dashboard_client.unlockProtectiveStop()
                    #     self.rtde_handler.ur_dashboard_client.closePopup()
                    #     self.rtde_handler.ur_dashboard_client.popup('Protective Stop Cleared!')
                    #     print('Protective Stop cleared!')
                    #     self.rtde_handler.connect_rtde_c()
                    #
                    # except Exception as e:
                    #     self.rtde_handler.ur_dashboard_client.popup('Error while trying to clear protective stop!')
                    #     print(f'Error clearing Protective Stop: {e}')

                else:
                    print(f'Unrecognized Stop Mode. Status bit: {status_bit}')

                status_bit = self.rtde_handler.rtde_r.getSafetyMode()

                await asyncio.sleep(check_interval)  # inner loop interval

            await asyncio.sleep(check_interval)  # outer loop interval

    async def moveX(self):
        if self.local_ur10e.STOP == 0:
            # stop current movement before starting new one
            try:
                if self.local_ur10e.is_moving:
                    rtde_handler.rtde_c.stopJ(self.local_ur10e.joint_accel, asynchronous=False)

                    while self.local_ur10e.is_moving:
                        await asyncio.sleep(0.01)

                if self.local_ur10e.move_type == 0:  # MoveL
                    target_tcp = pu.mm2m(pu.rpy2rv(self.local_ur10e.target_tcp))
                    self.rtde_handler.rtde_c.moveL(target_tcp, self.local_ur10e.linear_speed, self.local_ur10e.linear_accel,
                                                   asynchronous=True)  # True for non-blocking

                elif self.local_ur10e.move_type == 1:  # MoveJ
                    target_joint = pu.array_d2r(6, self.local_ur10e.target_joint)
                    self.rtde_handler.rtde_c.moveJ(target_joint, pu.d2r(self.local_ur10e.joint_speed),
                                                   pu.d2r(self.local_ur10e.joint_accel),
                                                   asynchronous=True)  # True for async (non-blocking)
                else:
                    print("Invalid move type!")
            except Exception as e:
                print(f"Exception while handling Move command: {e}")

        elif self.local_ur10e.STOP == 1:
            self.is_stopped = True
            print(f'debug: is_stopped: {self.is_stopped}')
            try:
                if self.local_ur10e.move_type == 0:  # MoveL
                    self.rtde_handler.rtde_c.stopL(max(self.local_ur10e.linear_accel, math.pi),
                                                   asynchronous=False)
                    # async=True sometimes drops control script. Difficult to reconnect.
                elif self.local_ur10e.move_type == 1:  # MoveJ
                    self.rtde_handler.rtde_c.stopJ(max(self.local_ur10e.joint_accel, math.pi),
                                                   asynchronous=False)
                    # async=False added benefit: easy to know when robot came to a stop.
                else:
                    print("Invalid move type for Stop command!")
            except Exception as e:
                print(f"Exception while handling Stop command: {e}")

            self.local_ur10e.reset_STOP_flag = 1  # resets stop bit after robot is stopped (gets sent to MW)
            while self.local_ur10e.STOP == 1:
                await asyncio.sleep(rtde_per)
            self.local_ur10e.reset_STOP_flag = 0

    def set_output_bits(self):
        for i in range(8):
            self.rtde_handler.rtde_io.setStandardDigitalOut(i, self.local_ur10e.target_standard_output_bits[i])

        for i in range(8):
            self.rtde_handler.rtde_io.setConfigurableDigitalOut(i, self.local_ur10e.target_configurable_output_bits[i])

        for i in range(2):
            self.rtde_handler.rtde_io.setToolDigitalOut(i, self.local_ur10e.target_tool_output_bits[i])

    # call functions separate in order to not block the event loop of receive_command()
    # while executing moveX() or set_output_bits()
    async def call_moveX(self):
        while True:
            if self.start_movement_flag:
                await self.moveX()
                self.start_movement_flag = False  # after moveX() is done

            await asyncio.sleep(rtde_per)

    async def call_set_output_bits(self):
        while True:
            if self.start_setting_output_bits:
                print('debug: received output_bit_command from MW!')
                self.set_output_bits()
                # after bits are set:
                self.start_setting_output_bits = False

            await asyncio.sleep(rtde_per)

    async def receive_commands(self):
        while True:
            try:
                [topic, message_received] = await self.zmq_handler.sub_socket.recv_multipart()
                message = json.loads(message_received.decode())
                self.local_ur10e.update_local_dataset(message)

                print(f"stop: {self.local_ur10e.STOP},"
                      f"move_type: {self.local_ur10e.move_type}")

                if topic == b"Move_Command":
                    self.start_movement_flag = True  # this calls moveX(self) method
                    # not calling moveX() directly from here so receive_commands() can continue running
                    # if called directly from here, it would block receive_commands() function
                elif topic == b"output_bit_command":
                    self.start_setting_output_bits = True
                    # not calling moveX() directly from here so receive_commands() can continue running
                    # if called directly from here, it would block receive_commands() function
                await asyncio.sleep(rtde_per)

            except KeyboardInterrupt:
                break

    async def send(self):
        while True:
            try:
                await self.local_ur10e.get_actual_from_robot()

                message = self.local_ur10e.gather_to_send()
                serialized_message = json.dumps(message).encode()

                await self.zmq_handler.pub_socket.send_multipart([b"Joint_States", serialized_message])

                await asyncio.sleep(rtde_per)
            except Exception as e:
                print(f"Error in function: send() {e}")

    async def run(self):
        print("\033[32mStarted ASYNC function!\033[0m")
        await asyncio.gather(self.send(), self.receive_commands(), self.check_status(), self.call_moveX(),
                             self.call_set_output_bits())


if __name__ == "__main__":
    zmq_handler = ZmqHandler()
    zmq_handler.connect()

    rtde_handler = RtdeHandler()
    rtde_handler.connect()

    async_handler = AsyncHandler(zmq_handler, rtde_handler)
    asyncio.run(async_handler.run())
