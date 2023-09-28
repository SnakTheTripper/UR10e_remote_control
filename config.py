ip_address_ur10 = "10.0.0.100"

ip_address_bridge = "10.0.0.225"
ip_address_MW = "10.0.0.225"
ip_address_flask_local = "10.0.0.225"
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

rtde_frequency = 500    # [1 - 500]
opcua_frequency = 100     # [1 - rtde_frequency]
