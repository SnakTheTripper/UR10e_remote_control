import json
import math
import sys
import threading
import time
import zmq
from flask import Flask, render_template, redirect
from flask_socketio import SocketIO
import config


class CentralRobotData:
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


central_data = CentralRobotData()

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
            'home_position': config.robot_home_position}
def d2r(deg):
    return deg * math.pi / 180
def send_movement():
    message = central_data.gather_to_send()
    serialized_message = json.dumps(message)
    pub_socket.send_multipart([b"Move_Commands", serialized_message.encode()])
    socketio.emit('update_target_positions',
                  {'target_joint_positions': central_data.target_joint, 'target_tcp_positions': central_data.target_tcp,
                   'speedJ': central_data.joint_speed, 'accelJ': central_data.joint_accel,
                   'speedL': central_data.linear_speed, 'accelL': central_data.linear_accel})
def update_current_positions():  # on web client
    global page_initialization
    while True:
        try:
            [topic, received_message] = sub_socket.recv_multipart()
            decoded_message = json.loads(received_message.decode())
            central_data.update_local_dataset(decoded_message)

            if central_data.move_type == 0:  # moveL
                socketio.emit('update_current', {'positions': central_data.current_tcp})
            elif central_data.move_type == 1:  # moveJ
                socketio.emit('update_current', {'positions': central_data.current_joint})

        except Exception as e:
            print(f"Error in receiving the actual joint positions!: {e}")


def sendButton(data):
    m_t = data["move_type"]
    central_data.move_type = m_t
    print(f'Move Type changed to JOINT: {central_data.move_type}')

    if central_data.move_type == 0:  # moveL
        pos = data["target_tcp_positions"]
        v = data["linear_speed"]
        a = data["linear_accel"]

        for i in range(6):
            central_data.target_tcp = pos
        central_data.linear_speed = v
        central_data.linear_accel = a

    elif central_data.move_type == 1:  # moveJ
        jp = data["target_joint_positions"]
        js = data["joint_speed"]
        ja = data["joint_accel"]

        for i in range(6):
            central_data.target_joint[i] = d2r(jp[i])
        central_data.joint_speed = d2r(js)  # speed slider
        central_data.joint_accel = d2r(ja)  # accel slider

    send_movement()
def stopButton():  # DOESN'T WORK AFTER CLASS INTEGRATION - NEEDS FIX
    temp_joint = central_data.target_joint
    temp_tcp = central_data.target_tcp

    central_data.STOP = True
    socketio.emit('STOP_button')  # for alert on webpage
    send_movement()  # send STOP signal

    central_data.set_target_to_current()  # target = current (so robot does not resume movement)

    central_data.STOP = False  # reset STOP bit to False (robot won't move: target is set to current)

    send_movement()

    central_data.target_joint = temp_joint
    central_data.target_tcp = temp_tcp

    socketio.emit('update_target_positions', {'target_joint_positions': central_data.target_joint,
                                              'target_tcp_positions': central_data.target_tcp,
                                              'speedJ': central_data.joint_speed,
                                              'accelJ': central_data.joint_accel,
                                              'speedL': central_data.linear_speed,
                                              'accelL': central_data.linear_accel})
def addToList():
    new_entry = None
    print("add to list press received")
    if central_data.move_type == 0:
        new_entry = [central_data.move_type, central_data.target_tcp[:], central_data.linear_speed,
                     central_data.linear_accel]
    elif central_data.move_type == 1:  # moveJ
        new_entry = [central_data.move_type, central_data.target_joint[:], central_data.joint_speed,
                     central_data.joint_accel]

    central_data.program_list.append(new_entry)
    socketio.emit('updateTable', {'program_list': central_data.program_list})
def deleteFromList(idToDelete):
    try:
        central_data.program_list.pop(idToDelete)
    except:
        print("Can't delete: Program List already empty")
def clearList():
    central_data.program_list = []
    print(f"Program List Cleared: {central_data.program_list}")
def runProgram():
    if len(central_data.program_list) > 0:
        i = 0
        try:
            while i < len(central_data.program_list) and not central_data.STOP:  # dynamically check if list length changes
                # central_data.program_list[i][0] <- is_moving bit
                central_data.target_joint = central_data.program_list[i][1]
                central_data.joint_speed = central_data.program_list[i][2]
                central_data.joint_accel = central_data.program_list[i][3]

                send_movement()

                print(f"Doing move nr. {i + 1}")
                time.sleep(1)  # needed between waypoints

                while central_data.is_moving:
                    time.sleep(0.5)
                    if central_data.STOP:
                        break

                if central_data.STOP:
                    print("STOP Button pressed")
                    break

                i += 1

            if not central_data.STOP:
                print("Program END")
                socketio.emit('program_end')
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
    central_data.move_type = 1  # moveJ
    config_data = gather_config_data_for_JavaScript()

    return render_template('JOINT_control.html', config_data=config_data)

@app.route('/tcp_control')
def TCP_control_page():
    print("TCP CONTROL PAGE OPENED - Move Type set")
    central_data.move_type = 0  # moveL
    config_data = gather_config_data_for_JavaScript()

    return render_template('TCP_control.html', config_data=config_data)


@socketio.on('button_press')
def handle_buttons(command_data):
    if command_data["action"] == "send":
        sendButton(command_data)
    elif command_data["action"] == "stop":
        stopButton()
    elif command_data["action"] == "addToList":
        addToList()
    elif command_data["action"] == "deleteFromList":  # just deletes the last waypoint
        deleteFromList(idToDelete=len(central_data.program_list) - 1)  # Deletes Last item. You can add idToDelete Later
    elif command_data["action"] == "clearList":
        clearList()
    elif command_data["action"] == "runProgram":
        runProgram()

    socketio.emit('updateTable', {'program_list': central_data.program_list})

@socketio.on('page_init')
def handle_moving_event():  # start current_position flow after page load for initialization
    global page_initialization

    page_initialization = True
    pub_socket.send_multipart([b"page_init", b'blank'])  # makes MWare send current positions to server (here)

    # Send signal to initialize target sliders
    socketio.emit('target_slider_init',
                  {'current_joint_positions': central_data.current_joint, 'program_list': central_data.program_list})

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
