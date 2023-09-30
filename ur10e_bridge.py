import asyncio
import json
import sys
import time
from asyncio.windows_events import WindowsSelectorEventLoopPolicy
import rtde_control
import rtde_receive
import zmq.asyncio
import config

asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
rtde_period = 1 / config.rtde_frequency    # 0.002s for 500Hz

class ZmqHandler:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.sub_socket = None
        self.pub_socket = None

    def connect(self):                      # connects to MiddleWare
        print("Binding ZMQ ports...")
        try:
            self.sub_socket = self.context.socket(zmq.SUB)
            self.sub_socket.bind(f"tcp://{config.ip_address_MW}:{config.port_mw_b}")
            self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://{config.ip_address_bridge}:{config.port_b_mw}")
        except:
            sys.exit("Can't bind ZMQ Ports")
        print("ZMQ Connected Successfully")

        return self.sub_socket, self.pub_socket


class RtdeHandler:
    def __init__(self):
        self.rtde_c = None
        self.rtde_r = None

    def connect(self):
        print("Connecting to robot...")

        try:
            self.rtde_c.disconnect()
            self.rtde_r.disconnect()
        except:
            time.sleep(0)

        try:
            self.rtde_c = rtde_control.RTDEControlInterface(config.ip_address_ur10)
            self.rtde_r = rtde_receive.RTDEReceiveInterface(config.ip_address_ur10)
        except RuntimeError as e:
            print(f"Make sure the robot is powered on!\nError: {e}")
            sys.exit('Start Robot!')

        print("Connected to UR10e Successfully")
        return self.rtde_c, self.rtde_r

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
        self.current_joint = self.rtde_r.getActualQ()
        self.current_tcp = self.rtde_r.getActualTCPPose()
        if any(element != 0 for element in self.rtde_r.getActualQd()):
            self.is_moving = True
        else:
            self.is_moving = False

    def update_local_dataset(self, data_dictionary):
        print('updating local (everything but current)')
        for key, value in data_dictionary.items():
            if key not in ['current_joint', 'current_tcp']:
                setattr(self, key, value)

    def gather_to_send(self):       # excludes unnecessary attributes
        return {key: value for key, value in self.__dict__.items() if key not in ['rtde_r', 'rtde_c', 'current_joint_speeds']}
class AsyncHandler:
    def __init__(self, zmq_handler, rtde_handler):
        self.zmq_handler = zmq_handler
        self.rtde_handler = rtde_handler
        self.local_robot_state = UR10e(rtde_handler.rtde_r, rtde_handler.rtde_c)

    async def check_status(self):
        check_interval = 1
        while True:
            status_bit = self.rtde_handler.rtde_r.getSafetyStatusBits()
            # print(rtde_r.getSafetyMode())     # can be used instead of .getSafetyStatusBits
            if status_bit != 1:  # is in some kind of protective stop
                print("Protective Stop Detected (or other non-normal mode). Please Enable Robot!")
                while status_bit != 1:
                    print('checking robot status...')
                    status_bit = self.rtde_handler.rtde_r.getSafetyStatusBits()
                    await asyncio.sleep(check_interval)
                print("Protective Stop Cleared!")
                self.rtde_handler.connect()
            await asyncio.sleep(check_interval)

    async def moveX(self, move_type, target_joint, target_tcp, v_joint, a_joint, v_lin, a_lin, stop):
        if not stop:
            if move_type == 0:  # MoveL
                self.rtde_handler.rtde_c.moveL(target_tcp, v_lin, a_lin, asynchronous=True)  # True for async (non-blocking)
            elif move_type == 1:  # MoveJ
                self.rtde_handler.rtde_c.moveJ(target_joint, v_joint, a_joint, asynchronous=True)  # True for async (non-blocking)
            else:
                print("Invalid move type!")

        else:
            if move_type == 0:  # MoveL
                self.rtde_handler.rtde_c.stopL(a_lin, True)  # True for async (non-blocking)
            elif move_type == 1:  # MoveJ
                self.rtde_handler.rtde_c.stopL(a_joint, True)  # True for async (non-blocking)

            self.rtde_handler.connect()

    async def receive(self):
        while True:
            try:
                [topic_received, message_received] = await self.zmq_handler.sub_socket.recv_multipart()
                message = json.loads(message_received.decode())
                self.local_robot_state.update_local_dataset(message)

                print(f"target: {self.local_robot_state.target_joint}, stop: {self.local_robot_state.STOP}, move type: {self.local_robot_state.move_type}")

                await self.moveX(self.local_robot_state.move_type, self.local_robot_state.target_joint, self.local_robot_state.target_tcp, self.local_robot_state.joint_speed, self.local_robot_state.joint_accel, self.local_robot_state.linear_speed, self.local_robot_state.linear_accel, self.local_robot_state.STOP)
                await asyncio.sleep(rtde_period)

            except KeyboardInterrupt:
                break

    async def send(self):   # Flow stops after STOP signal received even tho it reconnects (?)
        while True:
            await self.local_robot_state.get_actual_from_robot()
            message = self.local_robot_state.gather_to_send()   # uses an instance of class UR10e in this class method
            # print(message)

            serialized_message = json.dumps(message).encode()
            await self.zmq_handler.pub_socket.send_multipart([b"Joint_States", serialized_message])
            await asyncio.sleep(rtde_period)

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
