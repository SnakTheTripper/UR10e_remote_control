import asyncio
import json
import threading
import cv2
import time
from datetime import datetime

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


class ZmqSockets:
    def __init__(self):
        self.context = zmq.asyncio.Context()

        # SOCKETS

        self.to_bridge = self.context.socket(zmq.PUB)
        self.from_bridge = self.context.socket(zmq.SUB)
        self.flask_polling = self.context.socket(zmq.REQ)
        self.flask_update = self.context.socket(zmq.PUB)
        self.to_opcua = self.context.socket(zmq.PUB)
        self.from_opcua = self.context.socket(zmq.SUB)

        self.initialize_zmq_connections()
        self.subscribe_to_topics()

    def initialize_zmq_connections(self):
        try:
        # com with UR10e_bridge
            self.to_bridge.connect(f"tcp://{config.IP_BRIDGE}:{config.PORT_MW_B}")
            self.from_bridge.connect(f"tcp://{config.IP_BRIDGE}:{config.PORT_B_MW}")
            print('\033[32mUR10e Bridge ports connected!\033[0m')
        except Exception as e:
            print(f"\033[91mCan't connect to UR10e Bridge! {e}\033[0m")

        try:
        # com with OPCUA Server
            self.to_opcua.bind(f"tcp://{config.IP_MWARE}:{config.PORT_MW_OP}")
            self.from_opcua.bind(f"tcp://{config.IP_MWARE}:{config.PORT_OP_MW}")
            print('\033[32mOPCUA Server ports bound!\033[0m')
        except Exception as e:
            print(f"\033[91mCan't bind to OPCUA Server! {e}\033[0m")
        try:
        # com with Flask Server
            if config.ONLINE_MODE:
                self.flask_polling.connect(f"tcp://{config.IP_FLASK_CLOUD}:{config.PORT_FLASK_POLL}")
                self.flask_update.connect(f"tcp://{config.IP_FLASK_CLOUD}:{config.PORT_FLASK_UPDATE}")
                print(f'\033[32mConnected to Flask on {config.IP_FLASK_CLOUD}!\033[0m')
            else:
                self.flask_polling.connect(f"tcp://{config.IP_FLASK_LOCAL}:{config.PORT_FLASK_POLL}")
                self.flask_update.connect(f"tcp://{config.IP_FLASK_LOCAL}:{config.PORT_FLASK_UPDATE}")
                print(f'\033[32mConnected to Flask on {config.IP_FLASK_LOCAL}!\033[0m')
        except Exception as e:
            print(f"\033[91mCan't connect to Flask Server! {e}\033[0m")

        # print(
        #     f'Publish on port: {config.PORT_FLASK_POLL} & {config.PORT_FLASK_UPDATE} & {config.PORT_MW_B} & {config.PORT_MW_OP}\n'
        #     f'Listening on port: {config.PORT_FLASK_VIDEO_1} & {config.PORT_FLASK_VIDEO_2} & {config.PORT_FLASK_VIDEO_3} & {config.PORT_B_MW} & {config.PORT_OP_MW}')

    def subscribe_to_topics(self):
        self.from_bridge.setsockopt(zmq.SUBSCRIBE, b'Joint_States')

        self.from_opcua.setsockopt(zmq.SUBSCRIBE, b"Move_Command")
        self.from_opcua.setsockopt(zmq.SUBSCRIBE, b"output_bit_command")
        self.from_opcua.setsockopt(zmq.SUBSCRIBE, b"switchControl")


class UR10e:
    def __init__(self):
        self.current_joint = [0.0] * 6
        self.target_joint = config.robot_home_position_joint

        self.current_tcp = [0.0] * 6
        self.target_tcp = config.robot_home_position_tcp

        self.move_type = 1  # 0 = linear 1 = joint (represents last used move_type)
        self.control_mode = config.DEFAULT_CONTROL_MODE  # 0 = flask  1 = opcua

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

        self.mw_time = ''

        asyncio.gather(self.update_time())

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
                        'target_tool_output_bits',
                        'mw_time'
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
                        'tool_output_bits',
                        'mw_time'
                        ]}  # add input bits when added to bridge

    async def update_time(self):
        while True:
            now = datetime.now()
            self.mw_time = now.strftime("%H:%M:%S")

            await asyncio.sleep(0.1)


class FlaskHandler:

    class Cameras:
        def __init__(self):
            self.context = zmq.Context()
            self.camera_url_1 = config.camera_rtsp_link_1
            self.camera_url_2 = config.camera_rtsp_link_2
            self.camera_url_3 = config.camera_rtsp_link_3

            self.should_stream_1 = 1
            self.should_stream_2 = 1
            self.should_stream_3 = 1

            self.video_socket_1 = self.initialize_zmq(video_id=1)
            self.video_socket_2 = self.initialize_zmq(video_id=2)
            self.video_socket_3 = self.initialize_zmq(video_id=3)

        def initialize_zmq(self, video_id):
            video_socket = self.context.socket(zmq.PUB)
            port_attr = f"PORT_FLASK_VIDEO_{video_id}"

            if config.ONLINE_MODE:
                video_socket.connect(f"tcp://{config.IP_FLASK_CLOUD}:{getattr(config, port_attr)}")
            else:
                video_socket.connect(f"tcp://{config.IP_FLASK_LOCAL}:{getattr(config, port_attr)}")

            return video_socket

        def start(self, camera_id):

            # print(f'debug: Starting camera {camera_id}')

            # Map camera_id to corresponding attributes
            camera_url = getattr(self, f"camera_url_{camera_id}")
            video_socket = getattr(self, f"video_socket_{camera_id}")

            while True:
                # Create a VideoCapture object to connect to the camera
                cap = cv2.VideoCapture(camera_url)

                while getattr(self, f"should_stream_{camera_id}"):
                    # Capture a frame from the camera
                    ret, frame = cap.read()

                    if not ret:
                        print(f'Did not receive frame from camera {camera_id}!')
                        break

                    # Compress the frame
                    ret, buffer = cv2.imencode('.jpg', frame)
                    # Convert to bytes
                    frame_bytes = buffer.tobytes()

                    # Send the frame bytes over ZMQ
                    video_socket.send(frame_bytes)

                cap.release()
                time.sleep(1)

    def __init__(self, zmq_sockets, local_ur):
        self.zmq = zmq_sockets      # use self.zmq.<socket_name>

        # discard old REQs if a new one is sent out
        self.zmq.flask_polling.setsockopt(zmq.REQ_RELAXED, 1)

        self.local_ur10e = local_ur

        # periods
        self.standby_period = 0.2           # for frequency of 5 Hz
        self.flask_period = flask_per       # by default coming from project_utils.py

        # period between checking if standby or rtde period should be used in sending current states to Flask
        self.calculate_flask_frequency_period = 0.01

        self.polling_reply_detected = False

        # CAMERA STUFF

        self.cameras = self.Cameras()

        # camera heartbeat tracking
        self.camera_heartbeats = {1: time.time(), 2: time.time(), 3: time.time()}  # Initialize with current time
        self.heartbeat_timeout = 10  # 10 seconds timeout to stop streaming

        self.heartbeat_task = asyncio.create_task(self.check_camera_heartbeats())

        # start cameras threads
        self.video_thread_1 = threading.Thread(target=self.cameras.start, args=(1,))
        self.video_thread_2 = threading.Thread(target=self.cameras.start, args=(2,))
        self.video_thread_3 = threading.Thread(target=self.cameras.start, args=(3,))
        self.video_thread_1.start()
        self.video_thread_2.start()
        self.video_thread_3.start()

    async def polling_mechanism(self):
    # Periodically "poke" Flask_server.py to see if it has anything to respond
        while True:
            self.polling_reply_detected = False
            try:
                self.zmq.flask_polling.send(b'poll')
            except zmq.ZMQError as e:
                print(f"ZMQ Error: {e}")

            start_time = time.time()  # Initialize start time

            while not self.polling_reply_detected:
                await asyncio.sleep(flask_per)

                elapsed_time = time.time() - start_time  # Calculate elapsed time

                if elapsed_time >= 1.0:  # If 1 second has passed
                    print("Timeout reached, sending another poll.")
                    try:
                        # Reconnect logic
                        if config.ONLINE_MODE:
                            self.zmq.flask_polling.connect(f"tcp://{config.IP_FLASK_CLOUD}:{config.PORT_FLASK_POLL}")
                        else:
                            self.zmq.flask_polling.connect(f"tcp://{config.IP_FLASK_LOCAL}:{config.PORT_FLASK_POLL}")
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
                await self.zmq.flask_update.send_multipart([b"Joint_States", serialized_message])
            except Exception as e:
                print(f'Can not send update to Flask: {e}')

            await asyncio.sleep(flask_per)

    async def receive(self):
        topic = None
        serialized_message = None

        # receive from Flask
        while True:
            try:
                topic, serialized_message = await self.zmq.flask_polling.recv_multipart()
                self.polling_reply_detected = True
            except Exception as e:
                print(e)

            if topic == b'Move_Command':
                # forward to bridge
                await self.zmq.to_bridge.send_multipart([topic, serialized_message])
                print(f'debug: sent to bridge, STOP =  {self.local_ur10e.STOP}')

                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                message = json.loads(serialized_message.decode())

                print(f'debug: target tcp pose: {message}')

            elif topic == b'output_bit_command':
                print('debug: output_bit_command arrived!')

                # forward to bridge
                await self.zmq.to_bridge.send_multipart([topic, serialized_message])

                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))

            elif topic == b"switchControl":
                # set local control_mode value to opcua
                self.local_ur10e.control_mode = json.loads(serialized_message.decode())
                print(f'local control_mode set to {self.local_ur10e.control_mode}')

                # send control_mode update to OPCUA Server
                await self.zmq.to_opcua.send_multipart([b"switchControl", serialized_message])
                print(f'control_mode {self.local_ur10e.control_mode} sent to opcua server')

            elif topic == b'video':
                [video_id, should_stream] = json.loads(serialized_message.decode())
                self.camera_heartbeats[video_id] = time.time()  # Update the last heartbeat time
                setattr(self.cameras, f"should_stream_{video_id}", should_stream)
                # print(f'should_stream: {video_id}')

    async def check_camera_heartbeats(self):
        while True:
            current_time = time.time()
            for video_id, last_heartbeat in self.camera_heartbeats.items():
                if current_time - last_heartbeat > self.heartbeat_timeout:
                    # print(f"Heartbeat timeout for camera {video_id}. Stopping stream.")
                    setattr(self.cameras, f"should_stream_{video_id}", 0)
            await asyncio.sleep(1)  # Check every second

    # lower update rate for when robot is idle (not moving)

    # async def calculate_flask_frequency(self):
    #     while True:
    #         if self.local_ur10e.is_moving or self.local_ur10e.STOP:
    #             self.flask_period = flask_per
    #         else:
    #             self.flask_period = self.standby_period
    #
    #         # print(f'flask period: {self.flask_period}')
    #         await asyncio.sleep(self.calculate_flask_frequency_period)

    async def start_tasks(self):
        # create separate task for each class method
        tasks = [
            asyncio.create_task(self.polling_mechanism()),
            asyncio.create_task(self.send()),
            asyncio.create_task(self.receive())
        ]
        # run them concurrently
        await asyncio.gather(*tasks)

class OpcuaHandler:
    def __init__(self, zmq_sockets, local_ur):
        self.zmq = zmq_sockets
        self.local_ur10e = local_ur

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
                await self.zmq.to_opcua.send_multipart([b"update_package", serialized_message])
            except Exception as e:
                print(f'Can not send update to OPCUA: {e}')
            await asyncio.sleep(opcua_per)

    async def receive(self):  # receive from OPCUA
        topic = None
        serialized_message = None
        while True:
            try:
                topic, serialized_message = await self.zmq.from_opcua.recv_multipart()
            except Exception as e:
                print(f'Could not receive message from OPCUA Server: {e}')

            if topic == b'Move_Command':
                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                # forward to bridge
                await self.zmq.to_bridge.send_multipart([topic, serialized_message])

            elif topic == b"output_bit_command":
                # unpack and update local dataset
                self.local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))
                # forward to bridge
                await self.zmq.to_bridge.send_multipart([topic, serialized_message])

            elif topic == b"switchControl":
                # update local control_mode
                self.local_ur10e.control_mode = json.loads(serialized_message.decode())
                print(f'local control_mode set to {self.local_ur10e.control_mode}')

                # send control_mode update to Flask Server
                await self.zmq.flask_update.send_multipart([b"switchControl", serialized_message])
                print(f'control {self.local_ur10e.control_mode} sent to flask server')

    async def start_tasks(self):
        # create separate task for each class method
        tasks = [
            asyncio.create_task(self.send()),
            asyncio.create_task(self.receive()),
        ]
        # run them concurrently
        await asyncio.gather(*tasks)


async def receive_from_bridge(from_bridge_sock, local_ur10e):
    while True:
        topic, serialized_message = await from_bridge_sock.recv_multipart()
        local_ur10e.update_local_dataset(json.loads(serialized_message.decode()))  # blocking command


async def main():
    local_ur10e = UR10e()
    zmq_sockets = ZmqSockets()

    flask_handler = FlaskHandler(zmq_sockets, local_ur10e)
    opcua_handler = OpcuaHandler(zmq_sockets, local_ur10e)

    await asyncio.gather(flask_handler.start_tasks(),
                         opcua_handler.start_tasks(),
                         receive_from_bridge(zmq_sockets.from_bridge, local_ur10e))


if __name__ == "__main__":
    asyncio.run(main())
