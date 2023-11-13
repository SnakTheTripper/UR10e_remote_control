from enum import Enum

# --------------------- ONLINE ---------------------

ONLINE_MODE = False
FLASK_DOMAIN = 'http://www.uitrobot.com'

FLASK_USERNAME = 'beibei'
FLASK_PASSWORD = 'admin'

# ------------------ IP Addresses ------------------

IP_UR10e = "192.168.1.3"      # URSim on Snak's Laptop

IP_BRIDGE = "192.168.1.225"
IP_MWARE = "192.168.1.225"
IP_OPCUA = "192.168.1.225"

IP_FLASK_LOCAL = "192.168.1.225"
IP_FLASK_CLOUD = "51.120.242.4"

# ------------------ Ports ---------------------------

# Server Ports

PORT_FLASK_SERVER = 80          # port of Flask Server
PORT_OPCUA = 5001               # port of OPCUA Server

# ZMQ Ports

PORT_B_MW = 5553                # bridge to MW
PORT_MW_B = 5554                # MW to bridge

PORT_MW_OP = 5559               # MW to OPCUA
PORT_OP_MW = 5560               # OPCUA to MW

PORT_FLASK_POLL = 8091          # MW to Flask - and back
PORT_FLASK_UPDATE = 8092        # MW to Flask - update data

PORT_FLASK_VIDEO_1 = 5555       # live camera feed 1 to Flask
PORT_FLASK_VIDEO_2 = 5556       # live camera feed 2 to Flask
PORT_FLASK_VIDEO_3 = 5557       # live camera feed 3 to Flask

# ------------------ Frequencies ---------------------

RTDE_FREQ = 500             # [1 - rtde_frequency]
FLASK_FREQ = 50             # [1 - rtde_frequency]
OPCUA_FREQ = 50             # [1 - rtde_frequency]

# ------------------ Control Modes --------------------
class ControlModes(Enum):
    FLASK = 0
    OPCUA = 1

DEFAULT_CONTROL_MODE = ControlModes.FLASK.value

# ------------------ Robot Settings -------------------

robot_home_position_joint = [-180, -60.0, -120.0, -90.0, 90.0, 0.0]     # in deg
robot_home_position_tcp = [-385, 174, 595, 180, 0, -90]                 # in mm

joint_limits_lower = [-359, -190, -155, -359, -90, -359]        # joint 1 to 6
joint_limits_upper = [359, 10, 155, 359, 90, 359]               # joint 1 to 6
tcp_limits_lower = [-1000, -1000, 100, -180, -180, -180]        # XYZ in mm and RPY in deg
tcp_limits_upper = [1000, 1000, 1480, 180, 180, 180]            # XYZ in mm and RPY in deg

# --------------------- Camera --------------------------

camera_rtsp_link_1 = 'rtsp://192.168.1.228:554/stream1'
camera_rtsp_link_2 = 'rtsp://192.168.1.229:554/stream1'
camera_rtsp_link_3 = 'rtsp://192.168.1.231:554/stream1'

# ------------------ Starter Program ------------------

# have a predefined waypoint list on server start
STARTER_PROGRAM = [[1, [-180, -60, -120, -90, 90, 0], 15, 15],
                   [0, [-500, 174, 300, 180, 20, -90], 0.1, 0.1],
                   [0, [-500, -400, 300, 180, 20, -90], 0.1, 0.1],
                   [0, [-500, -400, 300, 180, 20, -180], 0.1, 0.1],
                   [0, [-800, -400, 300, 180, 20, -180], 0.1, 0.1],
                   [0, [-800, -400, 300, 180, 20, -270], 0.1, 0.1],
                   [0, [-800, 174, 300, 180, 20, -270], 0.1, 0.1],
                   [0, [-800, 174, 300, 180, 20, -360], 0.1, 0.1],
                   [0, [-500, 174, 300, 180, 20, -360], 0.1, 0.1],
                   [0, [-500, 200, 300, 180, 20, -360], 0.1, 0.1],
                   [1, [-180, -60, -120, -90, 90, 0], 30, 30]]
