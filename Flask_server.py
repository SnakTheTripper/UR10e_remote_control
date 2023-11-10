import eventlet

eventlet.monkey_patch()

from eventlet.green import zmq
from eventlet import wsgi

import json
import sys
import time
from queue import Queue
import base64

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_socketio import SocketIO
import config
import project_utils as pu
import logging

# logging.basicConfig(level=logging.ERROR)
log = logging.getLogger('eventlet.wsgi')
log.setLevel(logging.WARNING)

# Set then check Update frequency for Flask
freq_dict = pu.get_frequencies()
flask_per = freq_dict['flask_per']


def gather_config_data_for_JavaScript():
    actual_ip_flask = config.IP_FLASK_CLOUD if config.ONLINE_MODE else config.IP_FLASK_LOCAL
    return {'ip_address_flask': actual_ip_flask,
            'port_flask': config.PORT_FLASK_SERVER,
            'joint_limits_lower': config.joint_limits_lower,
            'joint_limits_upper': config.joint_limits_upper,
            'tcp_limits_lower': config.tcp_limits_lower,
            'tcp_limits_upper': config.tcp_limits_upper,
            'home_position_joint': config.robot_home_position_joint,
            'home_position_tcp': config.robot_home_position_tcp}


class UR10e:
    def __init__(self):
        self.current_joint = [0.0] * 6
        self.target_joint = [0.0] * 6

        self.current_tcp = [0.0] * 6
        self.target_tcp = [0.0] * 6

        # represents last used move_type
        self.move_type = 1  # 0 = linear 1 = joint
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

        self.program_list = []

        self.mw_time = 'flask init value'

    def update_local_dataset(self, data_dictionary):
        # print(f'debug {self.mw_time}')
        for key, value in data_dictionary.items():
            if key not in ['page_init']:
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
                'STOP': self.STOP
                }

    def gather_to_send_output_bits(self):
        return {'target_standard_output_bits': self.target_standard_output_bits,
                'target_configurable_output_bits': self.target_configurable_output_bits,
                'target_tool_output_bits': self.target_tool_output_bits}

    def set_target_to_current(self):
        self.target_tcp = self.current_tcp
        self.target_joint = self.current_joint


class MiddleWare:
    class ZmqSockets:
        def __init__(self):
            self.context = zmq.Context()

            self.polling_socket = self.context.socket(zmq.REP)
            self.update_socket = self.context.socket(zmq.SUB)
            self.video_socket_1 = self.context.socket(zmq.SUB)
            self.video_socket_2 = self.context.socket(zmq.SUB)
            self.video_socket_3 = self.context.socket(zmq.SUB)

            self.socket_setup()

        def socket_setup(self):
            # Connect to MW
            try:
                self.polling_socket.bind(f"tcp://*:{config.PORT_FLASK_POLL}")
                self.update_socket.bind(f"tcp://*:{config.PORT_FLASK_UPDATE}")
                self.video_socket_1.bind(f"tcp://*:{config.PORT_FLASK_VIDEO_1}")
                self.video_socket_2.bind(f"tcp://*:{config.PORT_FLASK_VIDEO_2}")
                self.video_socket_3.bind(f"tcp://*:{config.PORT_FLASK_VIDEO_3}")

                self.update_socket.setsockopt(zmq.SUBSCRIBE, b'Joint_States')
                self.update_socket.setsockopt(zmq.SUBSCRIBE, b'switchControl')
                self.video_socket_1.setsockopt_string(zmq.SUBSCRIBE, '')
                self.video_socket_2.setsockopt_string(zmq.SUBSCRIBE, '')
                self.video_socket_3.setsockopt_string(zmq.SUBSCRIBE, '')

                print(f'Bound ports {config.PORT_FLASK_POLL} & {config.PORT_FLASK_UPDATE} to listen to MW')
            except Exception as e:
                sys.exit(
                    f"Error with ports {config.PORT_FLASK_POLL}, {config.PORT_FLASK_UPDATE} or {config.PORT_FLASK_VIDEO_1}: {e}")

    def __init__(self):
        self.websocket = socket

        self.zmq = self.ZmqSockets()

        self.topic = None
        self.received_message = None

        self.web = WebMethods(self.websocket)

    def receive_polling(self):
        while True:
            message = self.zmq.polling_socket.recv()
            # print(f"I got this message: {message.decode()}")
            buttons.process_queue()

    def receive_from_mw(self):
        while True:
            try:
                [self.topic, self.received_message] = self.zmq.update_socket.recv_multipart()
                # print(f'message from WM: {json.loads(self.received_message.decode())}')
            except Exception as e:
                print(f"Error in receiving the actual joint positions!: {e}")

            if self.topic == b"Joint_States":
                decoded_message = json.loads(self.received_message.decode())
                local_ur10e.update_local_dataset(decoded_message)

            elif self.topic == b"switchControl":
                local_ur10e.control_mode = json.loads(self.received_message.decode())
                print(f'local control_mode set by OPCUA to {local_ur10e.control_mode}')
                self.websocket.emit('update_control_mode', {'control_mode': local_ur10e.control_mode})

            if local_ur10e.control_mode == 0:  # flask
                # update current, target is defined by web client
                self.web.update_current_positions()
                self.web.update_current_IO()

            elif local_ur10e.control_mode == 1:  # opcua
                # update current (from bridge) AND target (from opcua)
                self.web.update_current_positions()
                self.web.update_target_positions()
                self.web.update_current_IO()
                self.web.update_target_IO()

    def receive_video_feed_1(self):
        frame_bytes = None
        while True:
            try:
                # print('waiting for video feed')
                # Receive frame bytes from MW with ZMQ
                frame_bytes = self.zmq.video_socket_1.recv()
            except Exception as e:
                print(f"Error in receiving the video feed!: {e}")

            if frame_bytes is not None:
                base64_frame = base64.b64encode(frame_bytes).decode('utf-8')
                self.websocket.emit('video_feed_1', {'image': f"data:image/jpeg;base64,{base64_frame}"})
            else:
                print("frame_bytes is None. Skipping...")

    def receive_video_feed_2(self):
        frame_bytes = None
        while True:
            try:
                # print('waiting for video feed')
                # Receive frame bytes from MW with ZMQ
                frame_bytes = self.zmq.video_socket_2.recv()
            except Exception as e:
                print(f"Error in receiving the video feed!: {e}")

            if frame_bytes is not None:
                base64_frame = base64.b64encode(frame_bytes).decode('utf-8')
                self.websocket.emit('video_feed_2', {'image': f"data:image/jpeg;base64,{base64_frame}"})
            else:
                print("frame_bytes is None. Skipping...")

    def receive_video_feed_3(self):
        frame_bytes = None
        while True:
            try:
                # print('waiting for video feed')
                # Receive frame bytes from MW with ZMQ
                frame_bytes = self.zmq.video_socket_3.recv()
            except Exception as e:
                print(f"Error in receiving the video feed!: {e}")

            if frame_bytes is not None:
                base64_frame = base64.b64encode(frame_bytes).decode('utf-8')
                self.websocket.emit('video_feed_3', {'image': f"data:image/jpeg;base64,{base64_frame}"})
            else:
                print("frame_bytes is None. Skipping...")


class User(UserMixin):
    def __init__(self, username):
        self.id = username
def user_loader(user_id):
    return User(user_id)
class FlaskServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'MGTXdET0aoFuRnbAfUbRdmpG6K5X1SUF'  # Replace with a strong secret key
        self.username = config.FLASK_USERNAME
        self.password = config.FLASK_PASSWORD

        # setup of Flask-login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'

        self.login_manager.user_loader(user_loader)
        self.app_routes()

    def get_app(self):
        return self.app

    def app_routes(self):
        @self.app.route('/login', methods=["GET", "POST"])
        def login():
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                # Replace these with your hardcoded credentials
                if username == self.username and password == self.password:
                    user = User(username)
                    login_user(user)

                    session.permanent = False

                    return redirect(url_for('home'))
                else:
                    flash('Invalid username or password')
            return render_template('login.html')

        @self.app.route('/logout')
        def logout():
            logout_user()
            session.clear()
            return redirect(url_for('login'))

        @self.app.route('/', methods=["GET", "POST"])
        @login_required
        def index():
            return redirect('/home')

        @self.app.route('/home', methods=["GET", "POST"])
        @login_required
        def home():
            return render_template('home.html')

        @self.app.route('/joint_control', methods=["GET", "POST"])
        @login_required
        def JOINT_control_page():
            print("Joint Control Page Opened!")
            local_ur10e.move_type = 1  # moveJ
            config_data = gather_config_data_for_JavaScript()
            return render_template('JOINT_control.html', config_data=config_data)

        @self.app.route('/tcp_control', methods=["GET", "POST"])
        @login_required
        def TCP_control_page():
            print("TCP Control Page Opened!")
            local_ur10e.move_type = 0  # moveL
            config_data = gather_config_data_for_JavaScript()

            return render_template('TCP_control.html', config_data=config_data)

        @self.app.route('/video1')
        @login_required
        def video_page_1():
            print("Surveillance Video Page Opened! - 1")
            config_data = gather_config_data_for_JavaScript()
            return render_template('videos/video1.html', config_data=config_data)

        @self.app.route('/video2')
        @login_required
        def video_page_2():
            print("Surveillance Video Page Opened! - 2")
            config_data = gather_config_data_for_JavaScript()
            return render_template('videos/video2.html', config_data=config_data)

        @self.app.route('/video3')
        @login_required
        def video_page_3():
            print("Surveillance Video Page Opened! - 3")
            config_data = gather_config_data_for_JavaScript()
            return render_template('videos/video3.html', config_data=config_data)

        @self.app.route('/video_all')
        @login_required
        def video_page_all():
            print("Surveillance Video Page Opened! - ALL")
            config_data = gather_config_data_for_JavaScript()
            return render_template('videos/video_all.html', config_data=config_data)


class SocketIOEvents:
    def __init__(self, sck, btns):
        self.socket = sck
        self.web = WebMethods(self.socket)
        self.buttons = btns

        self.register_events()

    def register_events(self):
        @self.socket.on('button_press')
        def handle_buttons(command_data):
            action = command_data["action"]
            if action == "send":
                self.buttons.sendButton(command_data)
            elif action == "stop":
                self.buttons.stopButton()
            elif action == "send_output_bits":
                self.buttons.send_output_bits(command_data)
            elif action == "addToList":
                self.buttons.addToList(command_data)
            elif action == "deleteFromList":  # just deletes the last waypoint
                self.buttons.deleteFromList(
                    idToDelete=len(local_ur10e.program_list) - 1)  # Deletes Last item. You can add idToDelete Later
            elif action == "clearList":
                self.buttons.clearList()
            elif action == "runProgram":
                self.buttons.runProgram()
            elif action == "switchControl":
                self.buttons.switchControl()
            elif action == "toggleIoPanel":
                self.buttons.toggleIoPanel(command_data)
            elif action == "pauseVideo":
                self.buttons.pause_video(command_data)
            elif action == "resumeVideo":
                self.buttons.play_video(command_data)

            # update program list with every button press
            self.socket.emit('updateTable', {'program_list': local_ur10e.program_list})

        @self.socket.on('page_init')
        def page_init():
            # Send page initialization values
            self.web.send_page_initialization_values()

        @self.socket.on('keep_alive')
        def handle_keep_alive(message):
            # print(message["data"])
            self.socket.emit('keep_alive', {'message': 'Server is alive too'})


class WebMethods:
    def __init__(self, socketio):
        self.socket = socketio

    def update_current_positions(self):
        self.socket.emit('update_current_positions',
                         {'current_joint': local_ur10e.current_joint,
                          'current_tcp': local_ur10e.current_tcp,
                          "is_moving": local_ur10e.is_moving,
                          'mw_time': local_ur10e.mw_time})

    def update_target_positions(self):
        self.socket.emit('update_target_positions',
                         {'target_joint_positions': local_ur10e.target_joint,
                          'target_tcp_positions': local_ur10e.target_tcp,
                          'speedJ': local_ur10e.joint_speed,
                          'accelJ': local_ur10e.joint_accel,
                          'speedL': local_ur10e.linear_speed,
                          'accelL': local_ur10e.linear_accel})

    def update_current_IO(self):
        self.socket.emit('update_current_IO',
                         {'standard_input_bits': local_ur10e.standard_input_bits,
                          'configurable_input_bits': local_ur10e.configurable_input_bits,
                          'tool_input_bits': local_ur10e.tool_input_bits,
                          'standard_output_bits': local_ur10e.standard_output_bits,
                          'configurable_output_bits': local_ur10e.configurable_output_bits,
                          'tool_output_bits': local_ur10e.tool_output_bits})

    def update_target_IO(self):
        self.socket.emit('update_target_IO',
                         {
                             'target_standard_output_bits': local_ur10e.target_standard_output_bits,
                             'target_configurable_output_bits': local_ur10e.target_configurable_output_bits,
                             'target_tool_output_bits': local_ur10e.target_tool_output_bits,
                         })

    def send_page_initialization_values(self):
        self.socket.emit('page_init_values', {'current_joint_positions': local_ur10e.current_joint,
                                              'current_tcp_positions': local_ur10e.current_tcp,
                                              'current_joint_speed': local_ur10e.joint_speed,
                                              'current_joint_accel': local_ur10e.joint_accel,
                                              'current_tcp_speed': local_ur10e.linear_speed,
                                              'current_tcp_accel': local_ur10e.linear_accel,
                                              'program_list': local_ur10e.program_list,
                                              'control_mode': local_ur10e.control_mode,
                                              'standard_input_bits': local_ur10e.standard_input_bits,
                                              'configurable_input_bits': local_ur10e.configurable_input_bits,
                                              'tool_input_bits': local_ur10e.tool_input_bits,
                                              'standard_output_bits': local_ur10e.standard_output_bits,
                                              'configurable_output_bits': local_ur10e.configurable_output_bits,
                                              'tool_output_bits': local_ur10e.tool_output_bits,
                                              'io_panel_state': buttons.io_panel_state,
                                              'mw_time': local_ur10e.mw_time})


class Buttons:
    def __init__(self, socketio):
        self.socket = socketio
        self.web = WebMethods(self.socket)
        self.io_panel_state = 1

        self.global_stop_flag = False

        self.message_queue = Queue()

    def send_movement(self):
        message = local_ur10e.gather_to_send_command_values()  # gathers and sends relevant data from central_data to MW
        serialized_message = json.dumps(message).encode()
        self.message_queue.put([b"Move_Command", serialized_message])
        # send package to web clients, so it updates other clients too
        self.web.update_target_positions()

    def send_output_bits(self, data):
        # update local dataset with targets from website
        local_ur10e.target_standard_output_bits = data["target_standard_output_bits"]
        local_ur10e.target_configurable_output_bits = data["target_configurable_output_bits"]
        local_ur10e.target_tool_output_bits = data["target_tool_output_bits"]

        # send newly updated targets to MW only if flask is the active controlle
        if local_ur10e.control_mode == 0:  # flask
            message = local_ur10e.gather_to_send_output_bits()
            serialized_message = json.dumps(message).encode()
            self.message_queue.put([b"output_bit_command", serialized_message])
            # send package to web clients, so it updates other clients too
            self.web.update_target_IO()
        else:
            socket.emit('not_the_active_controller')

    def sendButton(self, data):
        m_t = data["move_type"]  # comes with every SEND button press (1 from joint, 0 from TCP control webpage)
        local_ur10e.move_type = m_t

        if local_ur10e.move_type == 0:  # moveL
            local_ur10e.target_tcp = data["target_tcp_positions"]
            local_ur10e.linear_speed = data["linear_speed"]
            local_ur10e.linear_accel = data["linear_accel"]

        elif local_ur10e.move_type == 1:  # moveJ
            local_ur10e.target_joint = data["target_joint_positions"]
            local_ur10e.joint_speed = data["joint_speed"]
            local_ur10e.joint_accel = data["joint_accel"]
            try:
                local_ur10e.target_tcp = data["target_tcp_positions"]
            except:
                pass

        if local_ur10e.control_mode == 0:
            self.send_movement()
        elif local_ur10e.control_mode == 1:
            socket.emit('not_the_active_controller')
            print('Control Mode is set to OPCUA!')
        else:
            print('Control Mode is set to Unknown! Check value of control_mode in Flask_server.py')

    def stopButton(self):
        if local_ur10e.control_mode == 0:  # flask
            local_ur10e.STOP = 1  # will be reset by reply from robot
            socket.emit('STOP_button')  # for alert on webpage
            self.send_movement()  # send STOP signal

            # robot will send reset_STOP_flag after coming to a complete stop

            while local_ur10e.reset_STOP_flag == 0:
                # print('debug: Waiting for resset_STOP_flag to turn to 1')
                time.sleep(flask_per)  # wait until reset_STOP_flag comes from robot

            # print('debug: reset_STOP_flag turned to 1! DONE! Resetting STOP to 0')
            local_ur10e.STOP = 0
            self.send_movement()

            # raise global stop flag for runProgram function to see (if program is running)

            self.global_stop_flag = True  # run_program_will lower it
        else:
            socket.emit('not_the_active_controller')

    def addToList(self, data):
        local_ur10e.move_type = data["move_type"]  # updated local move_type variable for each ADD button press
        pos = data["target_pos"]
        v = data["speed"]
        a = data["accel"]

        new_entry = [local_ur10e.move_type, pos, v, a]
        print(new_entry)
        local_ur10e.program_list.append(new_entry)
        self.socket.emit('updateTable', {'program_list': local_ur10e.program_list})

    def deleteFromList(self, idToDelete):
        try:
            local_ur10e.program_list.pop(idToDelete)
        except:
            print("Can't delete: Program List already empty")

        self.socket.emit('updateTable', {'program_list': local_ur10e.program_list})

    def clearList(self):
        local_ur10e.program_list = []
        print(f"Program List Cleared: {local_ur10e.program_list}")
        self.socket.emit('updateTable', {'program_list': local_ur10e.program_list})

    def runProgram(self):
        self.global_stop_flag = False  # just in case it remained raised
        if len(local_ur10e.program_list) > 0:
            print(f'debug:\n{local_ur10e.program_list}')
            i = 0
            try:
                # dynamically check if list length changes
                while i < len(local_ur10e.program_list) and local_ur10e.STOP == 0:
                    local_ur10e.move_type = local_ur10e.program_list[i][0]  # move_type J / L
                    if local_ur10e.move_type == 0:  # linear
                        local_ur10e.target_tcp = local_ur10e.program_list[i][1]
                        local_ur10e.linear_speed = local_ur10e.program_list[i][2]
                        local_ur10e.linear_accel = local_ur10e.program_list[i][3]

                    elif local_ur10e.move_type == 1:  # joint
                        local_ur10e.target_joint = local_ur10e.program_list[i][1]
                        local_ur10e.joint_speed = local_ur10e.program_list[i][2]
                        local_ur10e.joint_accel = local_ur10e.program_list[i][3]

                    self.send_movement()
                    print(f"Doing move nr. {i + 1}")

                    time.sleep(1)

                    while local_ur10e.is_moving:
                        if self.global_stop_flag:
                            break
                        time.sleep(flask_per)

                    time.sleep(1)  # between waypoints

                    if self.global_stop_flag:
                        break

                    i += 1

                if not self.global_stop_flag:
                    print("Program ran to the end")
                    socket.emit('program_end')
                else:
                    print('Program stopped!')
                    self.global_stop_flag = False
            except Exception as e:
                print(f"Error with running program. Check robot status! {e}")
        else:
            socket.emit('no_program_to_run')
            print("No program to Run")

    def switchControl(self):
        topic = b"switchControl"
        new_control_mode = None
        if local_ur10e.control_mode == 0:  # flask
            new_control_mode = 1  # opcua
        elif local_ur10e.control_mode == 1:  # opcua
            new_control_mode = 0  # flask
        else:
            print('\033[91mInvalid control_mode value in switchControl() function\033[0m')
            new_control_mode = 0

        print(f'New control_mode: {new_control_mode}')
        local_ur10e.control_mode = new_control_mode
        self.message_queue.put([topic, json.dumps(new_control_mode).encode()])

        self.socket.emit('update_control_mode', {'control_mode': local_ur10e.control_mode})

    def toggleIoPanel(self, data):
        self.io_panel_state = data["io_panel_state"]

    def pause_video(self, data):
        topic = b'video'
        should_play = 0

        id = data["video_id"]
        # print(data)
        msg = json.dumps([id, should_play]).encode()
        self.message_queue.put([topic, msg])

    def play_video(self, data):
        topic = b'video'
        should_play = 1

        id = data["video_id"]
        # print(data)
        msg = json.dumps([id, should_play]).encode()
        self.message_queue.put([topic, msg])

    def process_queue(self):
        if not self.message_queue.empty():
            topic, msg = self.message_queue.get()
            try:
                mw_handler.zmq.polling_socket.send_multipart([topic, msg])
            except Exception as e:
                print(e)
        else:
            topic = b'chill'
            msg = b'blank'
            mw_handler.zmq.polling_socket.send_multipart([topic, msg])


if __name__ == '__main__':
    local_ur10e = UR10e()  # local robot object state
    local_ur10e.program_list = config.STARTER_PROGRAM

    flask_server = FlaskServer()
    app = flask_server.get_app()
    app.config['UPLOAD_FOLDER'] = 'static'  # The directory where your images are stored

    socket = SocketIO(app, async_mode='eventlet',
                      cors_allowed_origins=[f"{config.FLASK_DOMAIN}",
                                            f"{config.FLASK_DOMAIN}:{config.PORT_FLASK_SERVER}",
                                            f"http://{config.IP_FLASK_LOCAL}",
                                            f"http://{config.IP_FLASK_LOCAL}:{config.PORT_FLASK_SERVER}"])

    buttons = Buttons(socket)
    SocketIOEvents(socket, buttons)

    mw_handler = MiddleWare()

    eventlet.spawn(mw_handler.receive_from_mw)
    eventlet.spawn(mw_handler.receive_polling)
    eventlet.spawn(mw_handler.receive_video_feed_1)
    eventlet.spawn(mw_handler.receive_video_feed_2)
    eventlet.spawn(mw_handler.receive_video_feed_3)

    # Start the Flask app with eventlet
    wsgi.server(eventlet.listen(("0.0.0.0", config.PORT_FLASK_SERVER)), app)
