import json
import math
import sys
import threading
import time
import zmq
from flask import Flask, render_template, redirect
from flask_socketio import SocketIO
from datetime import datetime, timedelta
import config

rtde_period = 1 / config.rtde_frequency
last_stop_time = None

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

        # only used locally

        self.program_list = []

    def update_local_dataset(self, data_dictionary):
        for key, value in data_dictionary.items():
            setattr(self, key, value)

    def gather_to_send(self):
        return {'target_joint': self.target_joint,
                'target_tcp': self.target_tcp,
                'move_type': self.move_type,
                'joint_speed': self.joint_speed,
                'joint_accel': self.joint_accel,
                'linear_speed': self.linear_speed,
                'linear_accel': self.linear_accel,
                'STOP': self.STOP, }

    def set_target_to_current(self):
        self.target_tcp = self.current_tcp
        self.target_joint = self.current_joint


local_robot_state = UR10e()
local_robot_state.program_list = config.starter_program

app = Flask(__name__)
socketio = SocketIO(app)

context = zmq.Context()
pub_socket = context.socket(zmq.PUB)
sub_socket = context.socket(zmq.SUB)

page_initialization = False

# Connect to MW
try:
    pub_socket.connect(f"tcp://{config.ip_address_flask_server}:{config.port_f_mw}")
    sub_socket.connect(f"tcp://{config.ip_address_MW}:{config.port_mw_f}")
    sub_socket.setsockopt(zmq.SUBSCRIBE, b"Joint_States")
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
def d2r(deg):
    return deg * math.pi / 180
def send_movement():
    message = local_robot_state.gather_to_send()         # gathers and sends relevant data from central_data to MW
    serialized_message = json.dumps(message)
    pub_socket.send_multipart([b"Move_Commands", serialized_message.encode()])
    # send package to web client
    socketio.emit('update_target_positions',
                  {'target_joint_positions': local_robot_state.target_joint,
                   'target_tcp_positions': local_robot_state.target_tcp,
                   'speedJ': local_robot_state.joint_speed,
                   'accelJ': local_robot_state.joint_accel,
                   'speedL': local_robot_state.linear_speed,
                   'accelL': local_robot_state.linear_accel})
def update_current_positions():  # on web client
    global page_initialization
    while True:
        try:
            [topic, received_message] = sub_socket.recv_multipart()
            decoded_message = json.loads(received_message.decode())
            local_robot_state.update_local_dataset(decoded_message)

            socketio.emit('update_current', {'joint_positions': local_robot_state.current_joint, 'tcp_positions': local_robot_state.current_tcp})

        except Exception as e:
            print(f"Error in receiving the actual joint positions!: {e}")
def sendButton(data):
    m_t = data["move_type"]     # comes with every SEND button press (1 from joint, 0 from TCP control webpage)
    local_robot_state.move_type = m_t

    if local_robot_state.move_type == 0:  # moveL
        pos = data["target_tcp_positions"]
        v = data["linear_speed"]
        a = data["linear_accel"]

        for i in range(3):
            local_robot_state.target_tcp[i] = pos[i] / 1000          # mm to m conversion
        for i in range(3, 6):
            local_robot_state.target_tcp[i] = d2r(pos[i])            # deg to rad conversion
        local_robot_state.linear_speed = v
        local_robot_state.linear_accel = a

    elif local_robot_state.move_type == 1:  # moveJ
        jp = data["target_joint_positions"]
        jv = data["joint_speed"]
        ja = data["joint_accel"]

        for i in range(6):
            local_robot_state.target_joint[i] = d2r(jp[i])
        local_robot_state.joint_speed = d2r(jv)  # speed slider
        local_robot_state.joint_accel = d2r(ja)  # accel slider

    send_movement()
def stopButton():  # DOESN'T WORK AFTER CLASS INTEGRATION - NEEDS FIX
    global last_stop_time
    now = datetime.now()
    if last_stop_time and now - last_stop_time < timedelta(seconds=3):
        print('Spamming stop button not permitted.')
    else:
        if local_robot_state.is_moving:     # don't send if not moving
            last_stop_time = now
            local_robot_state.STOP = True   # will be reset by reply from robot
            socketio.emit('STOP_button')  # for alert on webpage
            send_movement()  # send STOP signal

            # robot will reset STOP flag

            socketio.emit('update_target_positions', {'target_joint_positions': local_robot_state.target_joint,
                                                  'target_tcp_positions': local_robot_state.target_tcp,
                                                  'speedJ': local_robot_state.joint_speed,
                                                  'accelJ': local_robot_state.joint_accel,
                                                  'speedL': local_robot_state.linear_speed,
                                                  'accelL': local_robot_state.linear_accel})
        else:
            print('Robot not moving, Stop not sent')
def addToList(data):
    m_t = data["move_type"]     # updated local move_type variable for each ADD button press
    local_robot_state.move_type = m_t
    new_entry = None
    pos = data["target_pos"]
    v = data["speed"]
    a = data["accel"]

    print(pos, v, a)

    if local_robot_state.move_type == 0:
        for i in range(6):
            pos[i] = pos[i] / 1000          # linear: mm2m
        new_entry = [m_t, pos[:], v, a]
    elif local_robot_state.move_type == 1:
        for i in range(6):
            pos[i] = d2r(pos[i])            # joint:  d2r
        new_entry = [m_t, pos[:], d2r(v), d2r(a)]
    print(new_entry)
    local_robot_state.program_list.append(new_entry)
    socketio.emit('updateTable', {'program_list': local_robot_state.program_list})
def deleteFromList(idToDelete):
    try:
        local_robot_state.program_list.pop(idToDelete)
    except:
        print("Can't delete: Program List already empty")
def clearList():
    local_robot_state.program_list = []
    print(f"Program List Cleared: {local_robot_state.program_list}")
def runProgram():
    if len(local_robot_state.program_list) > 0:
        i = 0
        tmp_stop_flag = False
        print(local_robot_state.program_list)
        try:
            while i < len(local_robot_state.program_list) and not local_robot_state.STOP:  # dynamically check if list length changes
                local_robot_state.move_type = local_robot_state.program_list[i][0]     # move_type J / L
                print(local_robot_state.program_list)
                if local_robot_state.move_type == 0:    # linear
                    local_robot_state.target_tcp = local_robot_state.program_list[i][1]
                    local_robot_state.linear_speed = local_robot_state.program_list[i][2]
                    local_robot_state.linear_accel = local_robot_state.program_list[i][3]

                elif local_robot_state.move_type == 1:  # joint
                    local_robot_state.target_joint = local_robot_state.program_list[i][1]
                    local_robot_state.joint_speed = local_robot_state.program_list[i][2]
                    local_robot_state.joint_accel = local_robot_state.program_list[i][3]

                send_movement()

                print(f"Doing move nr. {i + 1}")
                time.sleep(2)  # needed between waypoints

                while local_robot_state.is_moving:
                    if local_robot_state.STOP:
                        tmp_stop_flag = True
                        print("STOP Button pressed")
                        break
                    time.sleep(rtde_period / 10)
                if tmp_stop_flag:
                    break

                i += 1

            if not tmp_stop_flag:
                print("Program ran to the end")
                socketio.emit('program_end')
            else:
                print('Program stopped!')
        except:
            print("Error with running program. Check robot status!")
    else:
        socketio.emit('no_program_to_run')
        print("No program to Run")


@app.route('/', methods=['GET', 'POST'])
def index():
    return redirect('/home')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/joint_control')
def JOINT_control_page():
    print("JOINT CONTROL PAGE OPENED - Move Type set")
    local_robot_state.move_type = 1  # moveJ
    config_data = gather_config_data_for_JavaScript()

    return render_template('JOINT_control.html', config_data=config_data)

@app.route('/tcp_control')
def TCP_control_page():
    print("TCP CONTROL PAGE OPENED - Move Type set")
    local_robot_state.move_type = 0  # moveL
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
        deleteFromList(idToDelete=len(local_robot_state.program_list) - 1)  # Deletes Last item. You can add idToDelete Later
    elif command_data["action"] == "clearList":
        clearList()
    elif command_data["action"] == "runProgram":
        runProgram()

    socketio.emit('updateTable', {'program_list': local_robot_state.program_list})

@socketio.on('page_init')
def handle_moving_event():  # start current_position flow after page load for initialization
    global page_initialization

    page_initialization = True
    pub_socket.send_multipart([b"page_init", b'blank'])  # makes MWare send current positions to server (here)

    # Send signal to initialize target sliders
    socketio.emit('target_slider_init',
                  {'current_joint_positions': local_robot_state.current_joint,
                   'current_tcp_positions': local_robot_state.current_tcp,
                   'program_list': local_robot_state.program_list})

@socketio.on('keep_alive')
def handle_keep_alive(message):
    # print(message["data"])
    socketio.emit('keep_alive', {'message': 'Server is alive too'})


if __name__ == '__main__':
    receiver_thread = threading.Thread(target=update_current_positions)
    print("ab to start receiver thread")
    receiver_thread.start()
    socketio.run(app, host=config.ip_address_flask_server, port=config.port_flask, debug=True,
                 allow_unsafe_werkzeug=True)
