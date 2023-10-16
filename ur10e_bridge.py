import math
from scipy.spatial.transform import Rotation as R
import numpy as np
import time
from asyncio.windows_events import WindowsSelectorEventLoopPolicy
import asyncio
import json
import sys

import rtde_control
import rtde_receive
import dashboard_client
import zmq.asyncio
import config
import config_utils

# disable when running on Linux based systems
asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

# Set then check Update frequency for RTDE & OPCUA
rtde_freq, rtde_per, opcua_freq, opcua_per = config_utils.get_frequencies()

def d2r(x):
    return x * math.pi / 180
def r2d(x):
    return x * 180 / math.pi

def rv2rpy(tcp_pose):
    rx, ry, rz = tcp_pose[3], tcp_pose[4], tcp_pose[5]
    rot_vec = np.array([rx, ry, rz])

    rotation = R.from_rotvec(rot_vec)
    rpy = rotation.as_euler('xyz', degrees=False)

    r, p, y = rpy
    tcp_pose[3], tcp_pose[4], tcp_pose[5] = r, p, y

    return tcp_pose

def rpy2rv(tcp_pose):
    r, p, y = tcp_pose[3], tcp_pose[4], tcp_pose[5]
    rpy = np.array([r, p, y])

    rotation = R.from_euler('xyz', rpy)
    rot_vec = rotation.as_rotvec()

    rx, ry, rz = rot_vec
    tcp_pose[3], tcp_pose[4], tcp_pose[5] = rx, ry, rz

    return tcp_pose

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
            self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"opcua_command")
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
            self.rtde_r = rtde_receive.RTDEReceiveInterface(config.ip_address_ur10, frequency=rtde_freq)
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
                self.rtde_c = rtde_control.RTDEControlInterface(config.ip_address_ur10, frequency=rtde_freq)
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
                self.connect_rtde_c()

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
        self.joint_accel = 0.1
        self.linear_speed = 0.1
        self.linear_accel = 0.1
        self.is_moving = False
        self.STOP = False

    async def get_actual_from_robot(self):
        try:
            self.current_joint = self.rtde_r.getActualQ()
            self.current_tcp = self.rtde_r.getActualTCPPose()
            self.current_tcp = rv2rpy(self.current_tcp)
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
                key in ['current_joint',
                        'current_tcp',
                        'is_moving',
                        'STOP']}     # needs to send this to reset the STOP flag in Flask_server.py

class AsyncHandler:
    def __init__(self, zmq_hndlr, rtde_hndlr):
        self.zmq_handler = zmq_hndlr
        self.rtde_handler = rtde_hndlr
        self.local_ur10e = UR10e(rtde_hndlr.rtde_r, rtde_hndlr.rtde_c)

    async def check_status(self):
        check_interval = 1      # seconds
        while True:
            if self.rtde_handler.rtde_c and not self.rtde_handler.rtde_c.isConnected():
                self.rtde_handler.rtde_c.reconnect()

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
            # stop current movement before starting new one
            if self.local_ur10e.is_moving:
                rtde_handler.rtde_c.stopJ(math.pi / 2, asynchronous=False)

            if move_type == 0:  # MoveL
                target_tcp = rpy2rv(target_tcp)
                self.rtde_handler.rtde_c.moveL(target_tcp, v_lin, a_lin, asynchronous=True)  # True for non-blocking

            elif move_type == 1:  # MoveJ
                print(self.local_ur10e.target_joint)
                self.rtde_handler.rtde_c.moveJ(target_joint, v_joint, a_joint, asynchronous=True)  # True for async (non-blocking)
            else:
                print("Invalid move type!")


        else:
            if move_type == 0:      # MoveL
                self.rtde_handler.rtde_c.stopL(max(a_lin, math.pi), asynchronous=False)       # async=True sometimes drops control script. Difficult to reconnect.
            elif move_type == 1:    # MoveJ
                self.rtde_handler.rtde_c.stopJ(max(a_lin, math.pi), asynchronous=False)     # async=False added benefit: easy to know when robot came to a stop.
            else:
                print("Invalid move type for Stop command!")

            self.local_ur10e.STOP = False  # resets stop bit after robot is stopped (gets sent to MW)

    async def receive(self):
        while True:
            try:
                [topic_received, message_received] = await self.zmq_handler.sub_socket.recv_multipart()
                message = json.loads(message_received.decode())
                self.local_ur10e.update_local_dataset(message)

                print(f"stop: {self.local_ur10e.STOP},"
                      f"move_type: {self.local_ur10e.move_type}")

                await self.moveX(self.local_ur10e.move_type, self.local_ur10e.target_joint,
                                 self.local_ur10e.target_tcp, self.local_ur10e.joint_speed,
                                 self.local_ur10e.joint_accel, self.local_ur10e.linear_speed,
                                 self.local_ur10e.linear_accel, self.local_ur10e.STOP)

                await asyncio.sleep(rtde_per)

            except KeyboardInterrupt:
                break

    async def send(self):
        while True:
            try:
                await self.local_ur10e.get_actual_from_robot()
                message = self.local_ur10e.gather_to_send()
                # print(message)

                serialized_message = json.dumps(message).encode()
                await self.zmq_handler.pub_socket.send_multipart([b"Joint_States", serialized_message])
                await asyncio.sleep(rtde_per)
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
