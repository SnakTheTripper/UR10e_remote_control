from opcua import ua

import config


def ur10e_platform_variables(idx, objects):

    ur10e_obj = objects.add_folder(idx, "ur10e Platform")

    ur10e_current_joint = ur10e_obj.add_object(idx, "1 UR10e Current Joint")
    current_joint_0 = ur10e_current_joint.add_variable(idx, "Current Base", 0.0)
    current_joint_1 = ur10e_current_joint.add_variable(idx, "Current Shoulder", 0.0)
    current_joint_2 = ur10e_current_joint.add_variable(idx, "Current Elbow", 0.0)
    current_joint_3 = ur10e_current_joint.add_variable(idx, "Current Wrist 1", 0.0)
    current_joint_4 = ur10e_current_joint.add_variable(idx, "Current Wrist 2", 0.0)
    current_joint_5 = ur10e_current_joint.add_variable(idx, "Current Wrist 3", 0.0)
    current_joint_0.set_writable()
    current_joint_1.set_writable()
    current_joint_2.set_writable()
    current_joint_3.set_writable()
    current_joint_4.set_writable()
    current_joint_5.set_writable()

    ur10e_target_joint = ur10e_obj.add_object(idx, "2 UR10e Target Joint")
    target_joint_0 = ur10e_target_joint.add_variable(idx, "Target Base", 0.0)
    target_joint_1 = ur10e_target_joint.add_variable(idx, "Target Shoulder", 0.0)
    target_joint_2 = ur10e_target_joint.add_variable(idx, "Target Elbow", 0.0)
    target_joint_3 = ur10e_target_joint.add_variable(idx, "Target Wrist 1", 0.0)
    target_joint_4 = ur10e_target_joint.add_variable(idx, "Target Wrist 2", 0.0)
    target_joint_5 = ur10e_target_joint.add_variable(idx, "Target Wrist 3", 0.0)
    target_joint_0.set_writable()
    target_joint_1.set_writable()
    target_joint_2.set_writable()
    target_joint_3.set_writable()
    target_joint_4.set_writable()
    target_joint_5.set_writable()

    ur10e_current_xyz = ur10e_obj.add_object(idx, "3 UR10e Current TCP")
    current_x = ur10e_current_xyz.add_variable(idx, "Current x", 0.45)
    current_y = ur10e_current_xyz.add_variable(idx, "Current y", 0.0)
    current_z = ur10e_current_xyz.add_variable(idx, "Current z", 0.7)
    current_rx = ur10e_current_xyz.add_variable(idx, "Current rx", 0.0)
    current_ry = ur10e_current_xyz.add_variable(idx, "Current ry", 0.0)
    current_rz = ur10e_current_xyz.add_variable(idx, "Current rz", 0.0)
    current_x.set_writable()
    current_y.set_writable()
    current_z.set_writable()
    current_rx.set_writable()
    current_ry.set_writable()
    current_rz.set_writable()

    ur10e_target_xyz = ur10e_obj.add_object(idx, "4 UR10e Target TCP")
    target_x = ur10e_target_xyz.add_variable(idx, "Target x", 0.45)
    target_y = ur10e_target_xyz.add_variable(idx, "Target y", 0.0)
    target_z = ur10e_target_xyz.add_variable(idx, "Target z", 0.7)
    target_rx = ur10e_target_xyz.add_variable(idx, "Target rx", 0.0)
    target_ry = ur10e_target_xyz.add_variable(idx, "Target ry", 0.0)
    target_rz = ur10e_target_xyz.add_variable(idx, "Target rz", 0.0)
    target_x.set_writable()
    target_y.set_writable()
    target_z.set_writable()
    target_rx.set_writable()
    target_ry.set_writable()
    target_rz.set_writable()

    control = ur10e_obj.add_object(idx, "5 UR10e Control Values")

    move_type = control.add_variable(idx, "move_type", 1)                   # 0 - linear, 1 - joint
    control_mode = control.add_variable(idx, "control_mode", config.default_control_mode)             # 0 - flask,  1 - opcua
    joint_speed = control.add_variable(idx, "Joint Speed", 10)
    joint_accel = control.add_variable(idx, "Joint Acceleration", 10)
    tcp_speed = control.add_variable(idx, "TCP Speed", 0.1)
    tcp_accel = control.add_variable(idx, "TCP Acceleration", 0.1)
    is_moving = control.add_variable(idx, "is_moving", 0)
    STOP = control.add_variable(idx, "STOP", 0)
    move_type.set_writable()      # 0 = linear 1 = joint
    control_mode.set_writable()
    joint_speed.set_writable()
    joint_accel.set_writable()
    tcp_speed.set_writable()
    tcp_accel.set_writable()
    STOP.set_writable()

    digital_inputs = ur10e_obj.add_object(idx, "6 UR10e Digital Input bits")
    input_bit_0 = digital_inputs.add_variable(idx, "input bit 0", 0)
    input_bit_1 = digital_inputs.add_variable(idx, "input bit 1", 0)
    input_bit_2 = digital_inputs.add_variable(idx, "input bit 2", 0)
    input_bit_3 = digital_inputs.add_variable(idx, "input bit 3", 0)
    input_bit_4 = digital_inputs.add_variable(idx, "input bit 4", 0)
    input_bit_5 = digital_inputs.add_variable(idx, "input bit 5", 0)
    input_bit_6 = digital_inputs.add_variable(idx, "input bit 6", 0)
    input_bit_7 = digital_inputs.add_variable(idx, "input bit 7", 0)
    input_bit_0.set_writable()
    input_bit_1.set_writable()
    input_bit_2.set_writable()
    input_bit_3.set_writable()
    input_bit_4.set_writable()
    input_bit_5.set_writable()
    input_bit_6.set_writable()
    input_bit_7.set_writable()

    digital_outputs = ur10e_obj.add_object(idx, "7 ur10e Digital Output bits")
    output_bit_0 = digital_outputs.add_variable(idx, "output bit 0", 0)
    output_bit_1 = digital_outputs.add_variable(idx, "output bit 1", 0)
    output_bit_2 = digital_outputs.add_variable(idx, "output bit 2", 0)
    output_bit_3 = digital_outputs.add_variable(idx, "output bit 3", 0)
    output_bit_4 = digital_outputs.add_variable(idx, "output bit 4", 0)
    output_bit_5 = digital_outputs.add_variable(idx, "output bit 5", 0)
    output_bit_6 = digital_outputs.add_variable(idx, "output bit 6", 0)
    output_bit_7 = digital_outputs.add_variable(idx, "output bit 7", 0)

    # why would these be writable dr. Fehér Aron?
    # output_bit_0.set_writable()
    # output_bit_1.set_writable()
    # output_bit_2.set_writable()
    # output_bit_3.set_writable()
    # output_bit_4.set_writable()
    # output_bit_5.set_writable()
    # output_bit_6.set_writable()
    # output_bit_7.set_writable()

    SEND_FLAG = ur10e_obj.add_variable(idx, "8 SEND FLAG", 0)   # send target values to MW when set to 1
    SEND_FLAG.set_writable()

    dataset = [
        current_joint_0,
        current_joint_1,
        current_joint_2,
        current_joint_3,
        current_joint_4,
        current_joint_5,

        target_joint_0,
        target_joint_1,
        target_joint_2,
        target_joint_3,
        target_joint_4,
        target_joint_5,

        current_x,
        current_y,
        current_z,
        current_rx,
        current_ry,
        current_rz,

        target_x,
        target_y,
        target_z,
        target_rx,
        target_ry,
        target_rz,

        move_type,
        control_mode,
        joint_speed,
        joint_accel,
        tcp_speed,
        tcp_accel,
        is_moving,

        input_bit_0,
        input_bit_1,
        input_bit_2,
        input_bit_3,
        input_bit_4,
        input_bit_5,
        input_bit_6,
        input_bit_7,

        output_bit_0,
        output_bit_1,
        output_bit_2,
        output_bit_3,
        output_bit_4,
        output_bit_5,
        output_bit_6,
        output_bit_7,

        SEND_FLAG,
        STOP
    ]
    return dataset
