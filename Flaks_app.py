import json
import math
import threading
import time
import zmq
from flask import Flask, render_template, redirect
from flask_socketio import SocketIO
import config

class CentralRobotData:
    def __init__(self):
        self.move_type = 1

        self.current_joint_positions = [0.0]*6
        self.current_joint_speeds = [0.0] * 6
        self.current_tcp_positions = [0.0]*6

        self.target_joint_positions = [0.0]*6
        self.target_tcp_positions = [0.0]*6

        self.joint_speed = 0.1
        self.joint_accel = 0.1
        self.tcp_speed = 0.1
        self.tcp_accel = 0.1

        self.is_moving = False
        self.STOP = False

        self.program_list = []

    def update_from_received_data(self, received_data):
        self.is_moving = received_data["is_moving"]
        self.current_joint_positions = received_data["current_joint_positions"]
        self.current_joint_speeds = received_data["current_joint_speeds"]

    def prepare_data_to_send(self):
        if self.move_type == 0:
            return {
                "move_type": self.move_type,
                "target_tcp_positions": self.target_tcp_positions,
                "linear_speed": self.tcp_speed,
                "linear_accel": self.tcp_accel,
                "stop": self.STOP
            }
        elif self.move_type == 1:
            return {
                "move_type": self.move_type,
                "target_joint_positions": self.target_joint_positions,
                "joint_speed": self.joint_speed,
                "joint_accel": self.joint_accel,
                "stop": self.STOP
            }

    def set_target_to_current(self):
        self.target_tcp_positions = self.current_tcp_positions
        self.target_joint_positions = self.current_joint_positions

central_data = CentralRobotData()

app = Flask(__name__)
socketio = SocketIO(app)

context = zmq.Context()
pub_socket = context.socket(zmq.PUB)
sub_socket = context.socket(zmq.SUB)

page_initialization = False


# Connect to UR10 BRIDGE
pub_socket.bind(f"tcp://{config.ip_address_flask_local}:{config.port_f_mw}")
sub_socket.bind(f"tcp://{config.ip_address_flask_local}:{config.port_mw_f}")
sub_socket.setsockopt(zmq.SUBSCRIBE, b"Joint_States")

def d2r(deg):
    return deg * math.pi / 180

def send_movement():
    message = central_data.prepare_data_to_send()
    serialized_message = json.dumps(message)
    pub_socket.send_multipart([b"Move_Commands", serialized_message.encode()])
    socketio.emit('update_target_positions', {'target_joint_positions': central_data.target_joint_positions, 'target_tcp_positions': central_data.target_tcp_positions, 'speedJ': central_data.joint_speed, 'accelJ': central_data.joint_accel, 'speedL': central_data.tcp_speed, 'accelL': central_data.tcp_accel})

def forward_current_positions():    # to web client
    while True:
        try:
            [topic, received_message] = sub_socket.recv_multipart()
            decoded_message = json.loads(received_message.decode())

            central_data.update_from_received_data(decoded_message)

            if central_data.is_moving or page_initialization:
                if central_data.move_type == 0:     # moveL
                    socketio.emit('update_current', {'positions': central_data.current_tcp_positions})
                elif central_data.move_type == 1:   # moveJ
                    socketio.emit('update_current', {'positions': central_data.current_joint_positions})

        except Exception as e:
            print(f"Error in receiving the actual joint positions!: {e}")

def sendButton(data):
    if central_data.move_type == 0:     # moveL
        pos = data["target_tcp_positions"]
        v = data["tcp_speed"]
        a = data["tcp_accel"]

        for i in range(6):
            central_data.target_tcp_positions = pos
        central_data.tcp_speed = v
        central_data.tcp_accel = a

    elif central_data.move_type == 1:   # moveJ
        jp = data["target_joint_positions"]
        js = data["joint_speed"]
        ja = data["joint_accel"]

        for i in range(6):
            central_data.target_joint_positions[i] = d2r(jp[i])
        central_data.joint_speed = d2r(js)  # speed slider
        central_data.joint_accel = d2r(ja)  # accel slider

    send_movement()

def stopButton():
    temp_joint = central_data.target_joint_positions
    temp_tcp = central_data.target_tcp_positions

    central_data.STOP = True
    send_movement()                     # send STOP signal

    time.sleep(1)

    central_data.set_target_to_current()        # target = current (so robot does not resume movement)
    central_data.STOP = False                   # reset STOP bit to False (robot won't move)
    send_movement()

    # reset the original target positions for client convenience

    central_data.target_joint_positions = temp_joint
    central_data.target_tcp_positions = temp_tcp
    socketio.emit('update_target_positions', {'target_joint_positions': central_data.target_joint_positions, 'target_tcp_positions': central_data.target_tcp_positions, 'speedJ': central_data.joint_speed, 'accelJ': central_data.joint_accel, 'speedL': central_data.tcp_speed, 'accelL': central_data.tcp_accel})

def addToList():
    new_entry = None
    print("add to list press received")
    if central_data.move_type == 0:
        new_entry = [central_data.move_type, central_data.target_tcp_positions[:], central_data.tcp_speed, central_data.tcp_accel]
    elif central_data.move_type == 1:   # moveJ
        new_entry = [central_data.move_type, central_data.target_joint_positions[:], central_data.joint_speed, central_data.joint_accel]

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
        try:
            for i in range(len(central_data.program_list)):
                central_data.target_joint_positions = central_data.program_list[i][1]
                central_data.joint_speed = central_data.program_list[i][2]
                central_data.joint_accel = central_data.program_list[i][3]

                send_movement()
                print(f"Doing move nr. {i+1}")
                time.sleep(1)
                while central_data.is_moving:
                    time.sleep(0.1)
                    if central_data.STOP:       # NOT IMPLEMENTED
                        break

                if central_data.STOP:
                    print("STOP Button pressed")
                    break

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
    print("JOINT CONTROL PAGE OPENED")
    central_data.move_type = 1  # moveJ
    print("move type joint set")
    return render_template('JOINT_control.html')

@app.route('/tcp_control')
def TCP_control_page():
    print("TCP CONTROL PAGE OPENED")
    central_data.move_type = 0  # moveL
    print("move type TCP set")
    return render_template('TCP_control.html')

@socketio.on('button_press')
def handle_buttons(command_data):
    if command_data["action"] == "send":
        sendButton(command_data)
    elif command_data["action"] == "stop":
        stopButton()
    elif command_data["action"] == "addToList":
        addToList()
    elif command_data["action"] == "deleteFromList":     # just deletes the last waypoint
        deleteFromList(idToDelete=len(central_data.program_list) - 1)   # Deletes Last item. You can add idToDelete Later
    elif command_data["action"] == "clearList":
        clearList()
    elif command_data["action"] == "runProgram":
        runProgram()

    socketio.emit('updateTable', {'program_list': central_data.program_list})

@socketio.on('set_moving')
def handle_moving_event(data):      # start current_position flow after page load for initialization
    global page_initialization

    page_initialization = True
    time.sleep(0.02)               # might need to tune this later based on testing with cloud
    page_initialization = False

    # Send signal to initialize target sliders
    socketio.emit('target_slider_init', {'current_joint_positions': central_data.current_joint_positions, 'program_list': central_data.program_list})

@socketio.on('keep_alive')
def handle_keep_alive(message):
    # print(message["data"])
    socketio.emit('keep_alive', {'message': 'Server is alive too'})

if __name__ == '__main__':
    receiver_thread = threading.Thread(target=forward_current_positions)
    receiver_thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
