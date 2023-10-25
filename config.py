from ur10e_programs import programs
from enum import Enum

# ------------------ IP Addresses ------------------

IP_UR10e = "10.0.0.100"      # URSim on Snak's Laptop

IP_BRIDGE = "10.0.0.225"
IP_MWARE = "10.0.0.225"
IP_FLASK_LOCAL = "10.0.0.225"
IP_OPCUA = "10.0.0.225"

PORT_UR_DASHBOARD = 29999   # port for UR dashboard client
PORT_FLASK = 5000           # port of Flask Server
PORT_OPCUA = 5001           # port of OPCUA Server

# ------------------ Ports ---------------------------

PORT_B_MW = 5555            # bridge to MW
PORT_MW_B = 5556            # MW to bridge
PORT_F_MW = 5557            # Flask to MW
PORT_MW_F = 5558            # MW to Flask
PORT_MW_OP = 5559           # MW to OPCUA
PORT_OP_MW = 5560           # OPCUA to MW

# ------------------ Frequencies ---------------------

RTDE_FREQ = 500             # [1 - 500] Hz
FLASK_FREQ = 500            # [1 - rtde_frequency]
OPCUA_FREQ = 20             # [1 - rtde_frequency]

# ------------------ Control Modes --------------------

class ControlModes(Enum):
    FLASK = 0
    OPCUA = 1

DEFAULT_MODE = ControlModes.FLASK.value

# ------------------ Starter Program ------------------

# have a predefined waypoint list on server start
STARTER_PROGRAM = programs.tcp_test

# ------------------ Robot Settings -------------------

robot_home_position_joint = [-180, -60.0, -120.0, -90.0, 90.0, 0.0]
robot_home_position_tcp = [-385, 174, 595, 180, 0, -90]          # in mm

joint_limits_lower = [-359, -190, -155, -359, -90, -359]        # joint 1 to 6 all in degrees
joint_limits_upper = [359, 10, 155, 359, 90, 359]               # joint 1 to 6
tcp_limits_lower = [-1000, -1000, 100, -180, -180, -180]        # xyz (mm)a nd rx ry rz (deg)
tcp_limits_upper = [1000, 1000, 1480, 180, 180, 180]            # xyz and rx ry rz


