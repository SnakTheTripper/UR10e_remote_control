ip_address_ur10 = "10.0.0.100"      # URSim on Snak's Laptop

ip_address_bridge = "10.0.0.225"
ip_address_MW = "10.0.0.225"
ip_address_flask_server = "10.0.0.225"
ip_address_opcua_server = "10.0.0.225"

port_flask = 5000       # port of Flask Server
port_opcua = 5001       # port of OPCUA Server

# ZMQ ports

port_b_mw = 5555        # bridge to MW
port_mw_b = 5556        # MW to bridge
port_f_mw = 5557        # Flask to MW
port_mw_f = 5558        # MW to Flask
port_mw_op = 5559       # MW to OPCUA
port_op_mw = 5560       # OPCUA to MW

rtde_frequency = 100    # [1 - 500] Hz
opcua_frequency = 1    # [1 - rtde_frequency]

robot_home_position = [0, -90, 0, -90, 0, 0]

joint_limits_lower = [-359, -190, -155, -359, -90, -359]     # joint 1 to 6  all in degrees
joint_limits_upper = [359, 10, 155, 359, 90, 359]     # joint 1 to 6
tcp_limits_lower = [0, 1, 2, 3, 4, 5]       # xyz and rx ry rz
tcp_limits_upper = [0, 1, 2, 3, 4, 5]       # xyz and rx ry rz
