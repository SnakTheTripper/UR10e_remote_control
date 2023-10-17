import json
import sys
import threading
import time
import zmq
from flask import Flask, render_template, redirect
from flask_socketio import SocketIO
from datetime import datetime, timedelta
import config
import config_utils

# Set then check Update frequency for RTDE & OPCUA
rtde_freq, rtde_per, opcua_freq, opcua_per = config_utils.get_frequencies()


class UR10e:
    def __init__(self):
        self.current_joint = [0.0] * 6
        self.target_joint = [0.0] * 6

        self.current_tcp = [0.0] * 6
        self.target_tcp = [0.0] * 6

        # represents last used move_type
        self.move_type = 1  # 0 = linear 1 = joint
        self.control_mode = config.default_control_mode  # 0 = flask  1 = opcua
        self.joint_speed = 10
        self.joint_accel = 10
        self.linear_speed = 0.1
        self.linear_accel = 0.1
        self.is_moving = 0
        self.STOP = 0
        self.reset_STOP_flag = 0

        self.input_bit_0 = 0
        self.input_bit_1 = 0
        self.input_bit_2 = 0
        self.input_bit_3 = 0
        self.input_bit_4 = 0
        self.input_bit_5 = 0
        self.input_bit_6 = 0
        self.input_bit_7 = 0

        self.output_bit_0 = 0
        self.output_bit_1 = 0
        self.output_bit_2 = 0
        self.output_bit_3 = 0
        self.output_bit_4 = 0
        self.output_bit_5 = 0
        self.output_bit_6 = 0
        self.output_bit_7 = 0

        self.page_init = False

        # only used locally

        self.program_list = []

    def update_local_dataset(self, data_dictionary):
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

    def set_target_to_current(self):
        self.target_tcp = self.current_tcp
        self.target_joint = self.current_joint


local_ur10e = UR10e()
local_ur10e.program_list = config.starter_program

app = Flask(__name__)
socketio = SocketIO(app)

context = zmq.Context()
pub_socket = context.socket(zmq.PUB)
sub_socket = context.socket(zmq.SUB)

page_initialization = False
global_stop_flag = False
last_stop_time = None

# Connect to MW
try:
    pub_socket.connect(f"tcp://{config.ip_address_flask_server}:{config.port_f_mw}")
    sub_socket.connect(f"tcp://{config.ip_address_MW}:{config.port_mw_f}")
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"Joint_States")
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"switchControl")
except Exception as e:
    sys.exit(f"Error with ports {config.port_f_mw} & {config.port_mw_f}: {e}")


def gather_config_data_for_JavaScript():
    return {'ip_address_flask': config.ip_address_flask_server,
            'port_flask': config.port_flask,
            'joint_limits_lower': config.joint_limits_lower,
            'joint_limits_upper': config.joint_limits_upper,
            'tcp_limits_lower': config.tcp_limits_lower,
            'tcp_limits_upper': config.tcp_limits_upper,
            'home_position_joint': config.robot_home_position_joint,
            'home_position_tcp': config.robot_home_position_tcp}

def send_movement():
    message = local_ur10e.gather_to_send_command_values()  # gathers and sends relevant data from central_data to MW
    serialized_message = json.dumps(message)
    pub_socket.send_multipart([b"Move_Commands", serialized_message.encode()])
    # send package to web client so it updates other clients too
    socketio.emit('update_target_positions',
                  {'target_joint_positions': local_ur10e.target_joint,
                   'target_tcp_positions': local_ur10e.target_tcp,
                   'speedJ': local_ur10e.joint_speed,
                   'accelJ': local_ur10e.joint_accel,
                   'speedL': local_ur10e.linear_speed,
                   'accelL': local_ur10e.linear_accel})


def receive_from_mw():  # on web client
    global page_initialization
    topic = None
    received_message = None
    while True:
        try:
            [topic, received_message] = sub_socket.recv_multipart()
        except Exception as e:
            print(f"Error in receiving the actual joint positions!: {e}")

        if topic == b"Joint_States":
            decoded_message = json.loads(received_message.decode())
            local_ur10e.update_local_dataset(decoded_message)

        elif topic == b"switchControl":
            local_ur10e.control_mode = json.loads(received_message.decode())
            print(f'local control_mode set by OPCUA to {local_ur10e.control_mode}')

        if local_ur10e.control_mode == 0:   # flask
            socketio.emit('update_current',
                          {'current_joint': local_ur10e.current_joint, 'current_tcp': local_ur10e.current_tcp})

        elif local_ur10e.control_mode == 1: # opcua
            socketio.emit('update_current',
                          {'current_joint': local_ur10e.current_joint, 'current_tcp': local_ur10e.current_tcp})
            socketio.emit('update_target_positions',
                          {'target_joint_positions': local_ur10e.target_joint,
                           'target_tcp_positions': local_ur10e.target_tcp,
                           'speedJ': local_ur10e.joint_speed,
                           'accelJ': local_ur10e.joint_accel,
                           'speedL': local_ur10e.linear_speed,
                           'accelL': local_ur10e.linear_accel})
                            # add output bits here

def sendButton(data):
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
        send_movement()
    elif local_ur10e.control_mode == 1:
        print('Control Mode is set to OPCUA!')
    else:
        print('Control Mode is set to Unknown! Check value of control_mode in Flask_server.py')


def stopButton():
    global last_stop_time, global_stop_flag
    now = datetime.now()
    if last_stop_time and now - last_stop_time < timedelta(seconds=2):
        print('Spamming stop button not permitted.')
    else:
        if local_ur10e.is_moving:           # only send if moving
            last_stop_time = now
            local_ur10e.STOP = 1            # will be reset by reply from robot
            socketio.emit('STOP_button')    # for alert on webpage
            send_movement()                 # send STOP signal

            # robot will send reset_STOP_flag after coming to a complete stop

            while local_ur10e.reset_STOP_flag == 0:
                print('debug: Waiting for resset_STOP_flag to turn to 1')
                time.sleep(rtde_per)        # wait until reset_STOP_flag comes from robot

            print('debug: reset_STOP_flag turned to 1! DONE! Resetting STOP to 0')
            local_ur10e.STOP = 0
            send_movement()

        else:
            print('Robot not moving, Stop not sent')

    # raise and lower global stop flag for runProgram function to see (if program is running)

    global_stop_flag = True
    time.sleep(2)
    global_stop_flag = False


def addToList(data):
    local_ur10e.move_type = data["move_type"]  # updated local move_type variable for each ADD button press
    pos = data["target_pos"]
    v = data["speed"]
    a = data["accel"]

    new_entry = [local_ur10e.move_type, pos, v, a]
    print(new_entry)
    local_ur10e.program_list.append(new_entry)
    socketio.emit('updateTable', {'program_list': local_ur10e.program_list})


def deleteFromList(idToDelete):
    try:
        local_ur10e.program_list.pop(idToDelete)
    except:
        print("Can't delete: Program List already empty")


def clearList():
    local_ur10e.program_list = []
    print(f"Program List Cleared: {local_ur10e.program_list}")


def runProgram():
    global global_stop_flag
    if len(local_ur10e.program_list) > 0:
        print(f'debig:\n{local_ur10e.program_list}')
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

                send_movement()

                print(f"Doing move nr. {i + 1}")
                time.sleep(1)  # between waypoints

                while local_ur10e.is_moving:
                    if global_stop_flag:
                        break
                    time.sleep(rtde_per)
                if global_stop_flag:
                    break

                i += 1

            if not global_stop_flag:
                print("Program ran to the end")
                socketio.emit('program_end')
            else:
                print('Program stopped!')
        except Exception as e:
            print(f"Error with running program. Check robot status! {e}")
    else:
        socketio.emit('no_program_to_run')
        print("No program to Run")


def switchControl():
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
    pub_socket.send_multipart([topic, json.dumps(new_control_mode).encode()])


@app.route('/', methods=['GET', 'POST'])
def index():
    return redirect('/home')


@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/joint_control')
def JOINT_control_page():
    print("JOINT CONTROL PAGE OPENED - Move Type set")
    local_ur10e.move_type = 1  # moveJ
    config_data = gather_config_data_for_JavaScript()

    return render_template('JOINT_control.html', config_data=config_data)


@app.route('/tcp_control')
def TCP_control_page():
    print("TCP CONTROL PAGE OPENED - Move Type set")
    local_ur10e.move_type = 0  # moveL
    config_data = gather_config_data_for_JavaScript()

    return render_template('TCP_control.html', config_data=config_data)


@socketio.on('button_press')
def handle_buttons(command_data):
    if command_data["action"] == "send":
        sendButton(command_data)
    elif command_data["action"] == "stop":
        stopButton()
    elif command_data["action"] == "addToList":
        addToList(command_data)
    elif command_data["action"] == "deleteFromList":  # just deletes the last waypoint
        deleteFromList(idToDelete=len(local_ur10e.program_list) - 1)  # Deletes Last item. You can add idToDelete Later
    elif command_data["action"] == "clearList":
        clearList()
    elif command_data["action"] == "runProgram":
        runProgram()
    elif command_data["action"] == "switchControl":
        switchControl()

    socketio.emit('updateTable', {'program_list': local_ur10e.program_list})


@socketio.on('page_init')
def handle_moving_event():  # start current_position flow after page load for initialization
    global page_initialization

    page_initialization = True
    pub_socket.send_multipart([b"page_init", b'blank'])  # makes MWare send current positions to server (here)

    # Send signal to initialize target sliders
    socketio.emit('target_slider_init', {'current_joint_positions': local_ur10e.current_joint,
                                         'current_tcp_positions': local_ur10e.current_tcp,
                                         'current_joint_speed': local_ur10e.joint_speed,
                                         'current_joint_accel': local_ur10e.joint_accel,
                                         'current_tcp_speed': local_ur10e.linear_speed,
                                         'current_tcp_accel': local_ur10e.linear_accel,
                                         'program_list': local_ur10e.program_list})


@socketio.on('keep_alive')
def handle_keep_alive(message):
    # print(message["data"])
    socketio.emit('keep_alive', {'message': 'Server is alive too'})


if __name__ == '__main__':
    receiver_thread = threading.Thread(target=receive_from_mw)
    receiver_thread.start()

    socketio.run(app, host=config.ip_address_flask_server, port=config.port_flask, debug=True,
                 allow_unsafe_werkzeug=True)
