import config
import numpy as np
import math
from scipy.spatial.transform import Rotation as R


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

def round_array(array, round_to_decimals):
    for i in range(len(array)):
        array[i] = round(array[i], round_to_decimals)
    return array

def d2r(x):
    return x * math.pi / 180

def r2d(x):
    return x * 180 / math.pi

def array_r2d(elements_to_convert, pos_array):
    for i in range(elements_to_convert):
        pos_array[i] = r2d(pos_array[i])
    return pos_array

def array_d2r(elements_to_convert, pos_array):
    for i in range(elements_to_convert):
        pos_array[i] = d2r(pos_array[i])
    return pos_array

def m2mm(pos_array):
    for i in range(3):
        pos_array[i] = pos_array[i] * 1000

    return pos_array

def mm2m(pos_array):
    for i in range(3):
        pos_array[i] = pos_array[i] / 1000

    return pos_array

def rv2rpy(tcp_pose):
    rx, ry, rz = tcp_pose[3], tcp_pose[4], tcp_pose[5]
    rot_vec = np.array([rx, ry, rz])

    rotation = R.from_rotvec(rot_vec)
    rpy = rotation.as_euler('yxz', degrees=True)

    r, p, y = rpy
    tcp_pose[3], tcp_pose[4], tcp_pose[5] = r, p, y

    return tcp_pose

def rpy2rv(tcp_pose):
    r, p, y = tcp_pose[3], tcp_pose[4], tcp_pose[5]
    rpy = np.array([r, p, y])

    rotation = R.from_euler('yxz', rpy, degrees=True)
    rot_vec = rotation.as_rotvec()

    rx, ry, rz = rot_vec
    tcp_pose[3], tcp_pose[4], tcp_pose[5] = rx, ry, rz

    return tcp_pose