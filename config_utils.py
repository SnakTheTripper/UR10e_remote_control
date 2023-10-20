import config


def get_frequencies():
    rtde_frequency = config.rtde_frequency
    rtde_period = 1 / rtde_frequency  # 0.002s for 500Hz

    flask_frequency = config.flask_frequency
    flask_period = 1 / flask_frequency

    opcua_frequency = config.opcua_frequency
    opcua_period = 1 / opcua_frequency

    if rtde_frequency > 500:
        print("RTDE Update frequency can not be higher than 500Hz")
        rtde_period = 0.002  # for 500Hz
        rtde_frequency = 500

    if flask_frequency > rtde_frequency:
        print('Flask Update frequency can not be higher than RTDE Update frequency')
        flask_period = rtde_period
        flask_frequency = rtde_frequency

    if opcua_frequency > rtde_frequency:
        print('OPCUA Update frequency can not be higher than RTDE Update frequency')
        opcua_period = rtde_period
        opcua_frequency = rtde_frequency

    return {
        'rtde_freq': rtde_frequency,
        'rtde_per': rtde_period,
        'flask_freq': flask_frequency,
        'flask_per': flask_period,
        'opcua_freq': opcua_frequency,
        'opcua_per': opcua_period
    }
