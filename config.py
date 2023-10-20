from ur10e_programs import programs

ip_address_ur10 = "10.0.0.100"      # URSim on Snak's Laptop

ip_address_bridge = "10.0.0.225"
ip_address_MW = "10.0.0.225"
ip_address_flask_server = "10.0.0.225"
ip_address_opcua_server = "10.0.0.225"

port_ur_dashboard = 29999   # port for UR dashboard client
port_flask = 5000           # port of Flask Server
port_opcua = 5001           # port of OPCUA Server

# ZMQ ports

port_b_mw = 5555        # bridge to MW
port_mw_b = 5556        # MW to bridge
port_f_mw = 5557        # Flask to MW
port_mw_f = 5558        # MW to Flask
port_mw_op = 5559       # MW to OPCUA
port_op_mw = 5560       # OPCUA to MW

rtde_frequency = 500    # [1 - 500] Hz
flask_frequency = 500   # [1 - rtde_frequency]
opcua_frequency = 20    # [1 - rtde_frequency]
# introduce Flask frequency too for the website!

default_control_mode = 0    # 0-Flask 1-OPCUA

robot_home_position_joint = [-180, -60.0, -120.0, -90.0, 90.0, 0.0]
robot_home_position_tcp = [-385, 174, 595, 180, 0, 90]        # in mm

joint_limits_lower = [-359, -190, -155, -359, -90, -359]        # joint 1 to 6 all in degrees
joint_limits_upper = [359, 10, 155, 359, 90, 359]               # joint 1 to 6
tcp_limits_lower = [-1000, -1000, 100, -180, -180, -180]        # xyz (mm)a nd rx ry rz (deg)
tcp_limits_upper = [1000, 1000, 1480, 180, 180, 180]            # xyz and rx ry rz

# have a predefined waypoint list on server start
starter_program = programs.tcp_test
