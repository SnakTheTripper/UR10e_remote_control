from asyncio.windows_events import WindowsSelectorEventLoopPolicy
import asyncio
import json
import socket
import sys
import time
import rtde_control
import rtde_receive
import dashboard_client
import zmq.asyncio
import config

# disable when running on Linux based systems
asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

rtde_period = 1 / config.rtde_frequency  # 0.002s for 500Hz

class ZmqHandler:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.sub_socket = None
        self.pub_socket = None

    def connect(self):  # connects to MiddleWare
        print("Binding ZMQ ports...")
        try:
            self.sub_socket = self.context.socket(zmq.SUB)
            self.sub_socket.bind(f"tcp://{config.ip_address_bridge}:{config.port_mw_b}")
            self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://{config.ip_address_bridge}:{config.port_b_mw}")
        except Exception as e:
            sys.exit(f"Can't bind ZMQ Ports: {e}")
        print("ZMQ Connected Successfully\n")

        return self.sub_socket, self.pub_socket


class RtdeHandler:
    def __init__(self):
        self.rtde_r = None
        self.rtde_c = None
        self.ur_dashboard_client = dashboard_client.DashboardClient(config.ip_address_ur10, config.port_ur_dashboard)

    def connect_rtde_r(self):
        print("Connecting RTDE Receive Interface...")
        try:
            self.rtde_r = rtde_receive.RTDEReceiveInterface(config.ip_address_ur10, frequency=config.rtde_frequency)
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
                self.rtde_c = rtde_control.RTDEControlInterface(config.ip_address_ur10, frequency=config.rtde_frequency)
                print("Connected to UR10e Successfully - RTDE Control\n")
            except RuntimeError as e:
                print(f"Make sure the robot is powered on!\nError: {e}")
                sys.exit('Start Robot!')

        # Reinitialization after Protective stop!

        else:
            print('RTDE Control Reinitializing...')
            try:
                self.rtde_c.disconnect()
                self.rtde_c.reconnect()
                print('RTDE Control Reinitialized successfully!')
            except Exception as e:
                print(f'Could not reconnect RTDE Control: {e}')

        return self.rtde_c

    def connect_ur_dashboard(self):   # RTDEScriptClient API
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
        ur_dashboard_socket = self.connect_ur_dashboard()
        return rtde_r, rtde_c, ur_dashboard_socket


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
        self.linear_speed = 0.1
        self.linear_accel = 0.1
        self.is_moving = False
        self.STOP = False

    async def get_actual_from_robot(self):
        try:
            self.current_joint = self.rtde_r.getActualQ()
            self.current_tcp = self.rtde_r.getActualTCPPose()
        except Exception as e:
            print(e)
        if any(element != 0 for element in self.rtde_r.getActualQd()):
            self.is_moving = True
        else:
            self.is_moving = False

    def update_local_dataset(self, data_dictionary):
        for key, value in data_dictionary.items():
            if key not in ['current_joint', 'current_tcp']:
                setattr(self, key, value)

    def gather_to_send(self):  # excludes unnecessary attributes
        return {key: value for key, value in self.__dict__.items() if
                key not in ['rtde_r', 'rtde_c', 'current_joint_speeds']}


class AsyncHandler:
    def __init__(self, zmq_handler, rtde_handler):
        self.zmq_handler = zmq_handler
        self.rtde_handler = rtde_handler
        self.local_robot_state = UR10e(rtde_handler.rtde_r, rtde_handler.rtde_c)

    async def check_status(self):
        check_interval = 1      # seconds
        while True:
            status_bit = self.rtde_handler.rtde_r.getSafetyMode()

            if status_bit != 1:      # not Normal Mode
                print("STOP DETECTED!")
            while status_bit != 1:
                if status_bit == 3:  # Protective Stop
                    try:
                        print('Protective Stop detected. Attempting to clear in 5 seconds...')
                        for i in range(5):
                            print(5-i)
                            await asyncio.sleep(1)
                        self.rtde_handler.ur_dashboard_client.unlockProtectiveStop()
                        print('Protective Stop cleared!')
                        self.rtde_handler.connect_rtde_c()

                    except Exception as e:
                        print(f'Error clearing Protective Stop: {e}')

                else:
                    print(f'Unrecognized Stop Mode. Status bit: {status_bit}')

                status_bit = self.rtde_handler.rtde_r.getSafetyMode()

                await asyncio.sleep(check_interval)     # inner loop interval

            await asyncio.sleep(check_interval)         # outer loop interval

    async def moveX(self, move_type, target_joint, target_tcp, v_joint, a_joint, v_lin, a_lin, stop):
        if not stop:
            if move_type == 0:  # MoveL
                if self.rtde_handler.rtde_c.isPoseWithinSafetyLimits(target_tcp):
                    self.rtde_handler.rtde_c.moveL(target_tcp, v_lin, a_lin, asynchronous=True)  # True for async (non-blocking)
            elif move_type == 1:  # MoveJ
                print(self.rtde_handler.rtde_c.isJointsWithinSafetyLimits(target_joint))
                self.rtde_handler.rtde_c.moveJ(target_joint, v_joint, a_joint, asynchronous=True)  # True for async (non-blocking)
            else:
                print("Invalid move type!")


        else:
            if move_type == 0:      # MoveL
                self.rtde_handler.rtde_c.stopL(a_lin, asynchronous=False)       # async=True sometimes drops control script. Difficult to reconnect.
            elif move_type == 1:    # MoveJ
                self.rtde_handler.rtde_c.stopJ(a_joint, asynchronous=False)     # async=False added benefit: easy to know when robot came to a stop.
            else:
                print("Invalid move type for Stop command!")

            self.local_robot_state.STOP = False  # resets stop bit after robot is stopped (gets sent to MW)


    async def receive(self):
        while True:
            try:
                [topic_received, message_received] = await self.zmq_handler.sub_socket.recv_multipart()
                message = json.loads(message_received.decode())
                self.local_robot_state.update_local_dataset(message)

                print(f"target: {self.local_robot_state.target_joint}, stop: {self.local_robot_state.STOP}, move type: {self.local_robot_state.move_type}")

                await self.moveX(self.local_robot_state.move_type, self.local_robot_state.target_joint,
                                 self.local_robot_state.target_tcp, self.local_robot_state.joint_speed,
                                 self.local_robot_state.joint_accel, self.local_robot_state.linear_speed,
                                 self.local_robot_state.linear_accel, self.local_robot_state.STOP)

                await asyncio.sleep(rtde_period / 2)

            except KeyboardInterrupt:
                break

    async def send(self):
        while True:
            try:
                await self.local_robot_state.get_actual_from_robot()
                message = self.local_robot_state.gather_to_send()
                # print(message)

                serialized_message = json.dumps(message).encode()
                await self.zmq_handler.pub_socket.send_multipart([b"Joint_States", serialized_message])
                await asyncio.sleep(rtde_period / 2)
            except Exception as e:
                print(f"Error in function: send() {e}")

    async def run(self):
        print("\033[32mStarted ASYNC function!\033[0m")
        await asyncio.gather(self.send(), self.receive(), self.check_status())


if __name__ == "__main__":
    zmq_handler = ZmqHandler()
    zmq_handler.connect()

    rtde_handler = RtdeHandler()
    rtde_handler.connect()

    async_handler = AsyncHandler(zmq_handler, rtde_handler)
    asyncio.run(async_handler.run())
