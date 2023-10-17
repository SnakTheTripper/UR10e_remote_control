import config

def get_frequencies():
    rtde_frequency = config.rtde_frequency
    rtde_period = 1 / config.rtde_frequency     # 0.002s for 500Hz

    opcua_frequency = config.opcua_frequency
    opcua_period = 1 / config.opcua_frequency

    if rtde_frequency > 500:
        print("RTDE Update frequency can not be higher than 500Hz")
        rtde_period = 0.002  # for 500Hz
        rtde_frequency = 500

    if opcua_frequency > rtde_frequency:
        print('OPCUA Update frequency can not be higher than RTDE Update frequency')
        opcua_period = rtde_period
        opcua_frequency = rtde_frequency

    return rtde_frequency, rtde_period, opcua_frequency, opcua_period
