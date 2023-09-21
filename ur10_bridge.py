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

class ZmqHandler:
    def __init__(self):
        self.context = zmq.asyncio.Context()
        self.sub_socket = None
        self.pub_socket = None

    def connect(self):                      # connects to MiddleWare
        print("Connecting to ZMQ ports...")
        try:
            self.sub_socket = self.context.socket(zmq.SUB)
            self.sub_socket.bind(f"tcp://{config.ip_address_bridge}:{config.port_mw_b}")
            self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"Move_Commands")
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://{config.ip_address_bridge}:{config.port_b_mw}")
        except:
            sys.exit("Can't connect to ZMQ Ports")
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
            time.sleep(0.01)

        try:
            self.rtde_c = rtde_control.RTDEControlInterface(config.ip_address_ur10)
            self.rtde_r = rtde_receive.RTDEReceiveInterface(config.ip_address_ur10)
        except RuntimeError as e:
            print(f"Make sure the robot is powered on!\nError: {e}")
            sys.exit("Start Robot!")
        print("Connected to UR10e Successfully")
        return self.rtde_c, self.rtde_r


class AsyncHandler:
    def __init__(self, zmq_handler, rtde_handler):
        self.zmq_handler = zmq_handler
        self.rtde_handler = rtde_handler

    async def check_status(self):
        check_interval = 0.5
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

    async def moveX(self, move_type, target_positions, v, a, stop):
        if not stop:
            if move_type == 0:  # MoveL
                self.rtde_handler.rtde_c.moveL(target_positions, v, a, asynchronous=True)  # True for async (non-blocking)
            elif move_type == 1:  # MoveJ
                self.rtde_handler.rtde_c.moveJ(target_positions, v, a, asynchronous=True)  # True for async (non-blocking)
            else:
                print("Invalid move type!")

        elif stop:
            if move_type == 0:  # MoveL
                self.rtde_handler.rtde_c.stopL(a, True)  # True for async (non-blocking)
            elif move_type == 1:  # MoveJ
                self.rtde_handler.rtde_c.stopL(a, True)  # True for async (non-blocking)

            rtde_handler.connect()

    async def receive(self):
        while True:
            try:
                [topic_received, message_received] = await self.zmq_handler.sub_socket.recv_multipart()
                message = json.loads(message_received.decode())

                move_type = message["move_type"]
                target_positions = None
                speed = None
                accel = None
                stop = None

                if move_type == 0:                  # moveL
                    target_positions = message["target_tcp_positions"]
                    speed = message["linear_speed"]
                    accel = message["linear_accel"]
                    stop = message["stop"]
                elif message["move_type"] == 1:     # moveJ
                    target_positions = message["target_joint_positions"]
                    speed = message["joint_speed"]
                    accel = message["joint_accel"]
                    stop = message["stop"]

                print(f"{target_positions}, stop: {stop}, move type: {move_type}")

                await self.moveX(move_type, target_positions, speed, accel, stop)
                await asyncio.sleep(0.02)

            except KeyboardInterrupt:
                break

    async def send(self):
        while True:
            # Gather current joint positions and JSpeeds from the robot
            current_joint_positions = self.rtde_handler.rtde_r.getActualQ()
            current_joint_speeds = self.rtde_handler.rtde_r.getActualQd()

            if any(element != 0 for element in current_joint_speeds):
                is_moving = True
            else:
                is_moving = False

            message = {"current_joint_positions": current_joint_positions, "current_joint_speeds": current_joint_speeds,
                       "is_moving": is_moving}
            serialized_message = json.dumps(message).encode()
            await self.zmq_handler.pub_socket.send_multipart([b"Joint_States", serialized_message])
            await asyncio.sleep(0.02)

    async def run(self):
        print("Starting ASYNC function...")
        await asyncio.gather(self.send(), self.receive(), self.check_status())


if __name__ == "__main__":
    zmq_handler = ZmqHandler()
    zmq_handler.connect()

    rtde_handler = RtdeHandler()
    rtde_handler.connect()

    async_handler = AsyncHandler(zmq_handler, rtde_handler)
    asyncio.run(async_handler.run())
