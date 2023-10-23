import json
import sys
import threading
import time
import zmq
from flask import Flask, render_template, redirect
from flask_socketio import SocketIO
from datetime import datetime, timedelta
import config
import project_utils as pu

# Set then check Update frequency for Flask
freq_dict = pu.get_frequencies()
flask_per = freq_dict['flask_per']

app = Flask(__name__)
socket = SocketIO(app)


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

        self.page_init = False
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

    def gather_to_send_output_bits(self):
        return {'target_standard_output_bits': self.target_standard_output_bits,
                'target_configurable_output_bits': self.target_configurable_output_bits,
                'target_tool_output_bits': self.target_tool_output_bits}

    def set_target_to_current(self):
        self.target_tcp = self.current_tcp
        self.target_joint = self.current_joint

class WebMethods:
    def __init__(self, socketio):
        self.socket = socketio

    def update_current_positions(self):
        self.socket.emit('update_current_positions',
                         {'current_joint': local_ur10e.current_joint,
                          'current_tcp': local_ur10e.current_tcp})

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
                                              'tool_output_bits': local_ur10e.tool_output_bits})

class Buttons:
    def __init__(self, socketio):
        self.socket = socketio
        self.web = WebMethods(self.socket)

        self.global_stop_flag = False

    def button_listener(self):
        @socket.on('button_press')
        def handle_buttons(command_data):
            action = command_data["action"]
            if action == "send":
                self.sendButton(command_data)
            elif action == "stop":
                self.stopButton()
            elif action == "send_output_bits":
                self.send_output_bits(command_data)
            elif action == "addToList":
                self.addToList(command_data)
            elif action == "deleteFromList":  # just deletes the last waypoint
                self.deleteFromList(
                    idToDelete=len(local_ur10e.program_list) - 1)  # Deletes Last item. You can add idToDelete Later
            elif action == "clearList":
                self.clearList()
            elif action == "runProgram":
                self.runProgram()
            elif action == "switchControl":
                self.switchControl()

            # update program list with every button press
            self.socket.emit('updateTable', {'program_list': local_ur10e.program_list})

    def send_movement(self):
        message = local_ur10e.gather_to_send_command_values()  # gathers and sends relevant data from central_data to MW
        serialized_message = json.dumps(message).encode()
        pub_socket.send_multipart([b"Move_Command", serialized_message])
        # send package to web clients, so it updates other clients too
        self.web.update_target_positions()

    def send_output_bits(self, data):
        # update local dataset with targets from website
        local_ur10e.target_standard_output_bits = data["target_standard_output_bits"]
        local_ur10e.target_configurable_output_bits = data["target_configurable_output_bits"]
        local_ur10e.target_tool_output_bits = data["target_tool_output_bits"]

        # send newly updated targets to MW
        message = local_ur10e.gather_to_send_output_bits()
        serialized_message = json.dumps(message).encode()
        pub_socket.send_multipart([b"output_bit_command", serialized_message])
        # send package to web clients, so it updates other clients too
        self.web.update_target_IO()

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
            print('Control Mode is set to OPCUA!')
        else:
            print('Control Mode is set to Unknown! Check value of control_mode in Flask_server.py')

    def stopButton(self):
        if local_ur10e.is_moving:  # only send if moving
            local_ur10e.STOP = 1  # will be reset by reply from robot
            socket.emit('STOP_button')  # for alert on webpage
            self.send_movement()  # send STOP signal

            # robot will send reset_STOP_flag after coming to a complete stop

            while local_ur10e.reset_STOP_flag == 0:
                print('debug: Waiting for resset_STOP_flag to turn to 1')
                time.sleep(flask_per)  # wait until reset_STOP_flag comes from robot

            print('debug: reset_STOP_flag turned to 1! DONE! Resetting STOP to 0')
            local_ur10e.STOP = 0
            self.send_movement()

        else:
            print('Robot not moving, Stop not sent')

        # raise global stop flag for runProgram function to see (if program is running)

        self.global_stop_flag = True  # run_program_will lower it

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
                        self.global_stop_flag = False
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
        pub_socket.send_multipart([topic, json.dumps(new_control_mode).encode()])

        self.socket.emit('update_control_mode', {'control_mode': local_ur10e.control_mode})


def zmq_connect_to_mw(pub_sock, sub_sock):
    # Connect to MW
    try:
        pub_sock.connect(f"tcp://{config.ip_address_flask_server}:{config.port_f_mw}")
        sub_sock.connect(f"tcp://{config.ip_address_MW}:{config.port_mw_f}")

        sub_sock.setsockopt(zmq.SUBSCRIBE, b"Joint_States")
        sub_sock.setsockopt(zmq.SUBSCRIBE, b"switchControl")
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


def receive_from_mw():  # on web client
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
            socket.emit('update_control_mode', {'control_mode': local_ur10e.control_mode})

        if local_ur10e.control_mode == 0:  # flask
            # update current, target is defined by web client
            web.update_current_positions()
            web.update_current_IO()

        elif local_ur10e.control_mode == 1:  # opcua
            # update current (from bridge) AND target (from opcua)
            web.update_current_positions()
            web.update_target_positions()
            web.update_current_IO()
            web.update_target_IO()


@app.route('/')
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


@socket.on('page_init')
def page_init():  # start current_position flow after page load for initialization
    # Send page initialization values
    web.send_page_initialization_values()

@socket.on('keep_alive')
def handle_keep_alive(message):
    # print(message["data"])
    socket.emit('keep_alive', {'message': 'Server is alive too'})


if __name__ == '__main__':
    web = WebMethods(socket)  # for updating web clients

    local_ur10e = UR10e()  # local robot object state
    local_ur10e.program_list = config.starter_program

    context = zmq.Context()
    pub_socket = context.socket(zmq.PUB)
    sub_socket = context.socket(zmq.SUB)

    zmq_connect_to_mw(pub_socket, sub_socket)

    buttons = Buttons(socket)
    buttons.button_listener()  # start @socket.on button event registering

    receiver_thread = threading.Thread(target=receive_from_mw)
    receiver_thread.start()

    socket.run(app, host=config.ip_address_flask_server, port=config.port_flask, debug=True,
               allow_unsafe_werkzeug=True)
