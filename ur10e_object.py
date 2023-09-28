def ur10e_platform_variables(idx, objects):

    ur10e_obj = objects.add_folder(idx, "ur10e Platform")

    ur10e_current_joint = ur10e_obj.add_object(idx, "1 ur10e Current Joint")
    current_joint_0 = ur10e_current_joint.add_variable(idx, "ur10e A1 Current", 0.0)
    current_joint_1 = ur10e_current_joint.add_variable(idx, "ur10e A2 Current", -90.0)
    current_joint_2 = ur10e_current_joint.add_variable(idx, "ur10e A3 Current", 0.0)
    current_joint_3 = ur10e_current_joint.add_variable(idx, "ur10e A4 Current", -90.0)
    current_joint_4 = ur10e_current_joint.add_variable(idx, "ur10e A5 Current", 0.0)
    current_joint_5 = ur10e_current_joint.add_variable(idx, "ur10e A6 Current", 0.0)
    current_joint_0.set_writable()
    current_joint_1.set_writable()
    current_joint_2.set_writable()
    current_joint_3.set_writable()
    current_joint_4.set_writable()
    current_joint_5.set_writable()

    ur10e_target_joint = ur10e_obj.add_object(idx, "2 ur10e Target Joint")
    target_joint_0 = ur10e_target_joint.add_variable(idx, "ur10e A1 Target", 0.0)
    target_joint_1 = ur10e_target_joint.add_variable(idx, "ur10e A2 Target", -90.0)
    target_joint_2 = ur10e_target_joint.add_variable(idx, "ur10e A3 Target", 0.0)
    target_joint_3 = ur10e_target_joint.add_variable(idx, "ur10e A4 Target", -90.0)
    target_joint_4 = ur10e_target_joint.add_variable(idx, "ur10e A5 Target", 0.0)
    target_joint_5 = ur10e_target_joint.add_variable(idx, "ur10e A6 Target", 0.0)
    # ?????
    target_joint_positions = ur10e_target_joint.add_variable(idx, "ur10e Target Joint Positions", "{}")
    # ?????
    target_joint_0.set_writable()
    target_joint_1.set_writable()
    target_joint_2.set_writable()
    target_joint_3.set_writable()
    target_joint_4.set_writable()
    target_joint_5.set_writable()
    target_joint_positions.set_writable()

    ur10e_current_xyz = ur10e_obj.add_object(idx, "3 ur10e Current xyz")
    current_x = ur10e_current_xyz.add_variable(idx, "ur10e x Current", 0.45)
    current_y = ur10e_current_xyz.add_variable(idx, "ur10e y Current", 0.0)
    current_z = ur10e_current_xyz.add_variable(idx, "ur10e z Current", 0.7)
    current_rx = ur10e_current_xyz.add_variable(idx, "ur10e rx Current", 0.0)
    current_ry = ur10e_current_xyz.add_variable(idx, "ur10e ry Current", 0.0)
    current_rz = ur10e_current_xyz.add_variable(idx, "ur10e rz Current", 0.0)
    current_x.set_writable()
    current_y.set_writable()
    current_z.set_writable()
    current_rx.set_writable()
    current_ry.set_writable()
    current_rz.set_writable()

    ur10e_target_xyz = ur10e_obj.add_object(idx, "4 ur10e target xyz")
    target_x = ur10e_target_xyz.add_variable(idx, "ur10e x target", 0.45)
    target_y = ur10e_target_xyz.add_variable(idx, "ur10e y target", 0.0)
    target_z = ur10e_target_xyz.add_variable(idx, "ur10e z target", 0.7)
    target_rx = ur10e_target_xyz.add_variable(idx, "ur10e rx target", 0.0)
    target_ry = ur10e_target_xyz.add_variable(idx, "ur10e ry target", 0.0)
    target_rz = ur10e_target_xyz.add_variable(idx, "ur10e rz target", 0.0)
    target_TCP_positions = ur10e_target_xyz.add_variable(idx, "ur10e target TCP Positions", "{}")
    target_x.set_writable()
    target_y.set_writable()
    target_z.set_writable()
    target_rx.set_writable()
    target_ry.set_writable()
    target_rz.set_writable()
    target_TCP_positions.set_writable()

    control = ur10e_obj.add_object(idx, "5 ur10e Control")
    move_type = control.add_variable(idx, "ur10e target Position Format", 0.0)
    home_position = control.add_variable(idx, "ur10e Home Position", 0.0)
    joint_speed = control.add_variable(idx, "ur10e Joint Speed", 0.1)
    joint_acceleration = control.add_variable(idx, "ur10e Joint Acceleration", 0.1)
    tcp_speed = control.add_variable(idx, "ur10e TCP Speed", 0.0)
    tcp_acceleration = control.add_variable(idx, "ur10e TCP Acceleration", 0.0)
    moving_flag = control.add_variable(idx, "ur10e Moving Flag", 0.0)
    move_type.set_writable()      # 0 = linear 1 = joint
    home_position.set_writable()
    joint_speed.set_writable()
    joint_acceleration.set_writable()
    tcp_speed.set_writable()
    tcp_acceleration.set_writable()
    moving_flag.set_writable()

    digital_inputs = ur10e_obj.add_object(idx, "8 ur10e Digital Input bits")
    input_bit_0 = digital_inputs.add_variable(idx, "ur10e input bit 0", False)
    input_bit_1 = digital_inputs.add_variable(idx, "ur10e input bit 1", False)
    input_bit_2 = digital_inputs.add_variable(idx, "ur10e input bit 2", False)
    input_bit_3 = digital_inputs.add_variable(idx, "ur10e input bit 3", False)
    input_bit_4 = digital_inputs.add_variable(idx, "ur10e input bit 4", False)
    input_bit_5 = digital_inputs.add_variable(idx, "ur10e input bit 5", False)
    input_bit_6 = digital_inputs.add_variable(idx, "ur10e input bit 6", False)
    input_bit_7 = digital_inputs.add_variable(idx, "ur10e input bit 7", False)
    input_bit_0.set_writable()
    input_bit_1.set_writable()
    input_bit_2.set_writable()
    input_bit_3.set_writable()
    input_bit_4.set_writable()
    input_bit_5.set_writable()
    input_bit_6.set_writable()
    input_bit_7.set_writable()

    digital_outputs = ur10e_obj.add_object(idx, "8 ur10e Digital Output bits")
    output_bit_0 = digital_outputs.add_variable(idx, "ur10e output bit 0", False)
    output_bit_1 = digital_outputs.add_variable(idx, "ur10e output bit 1", False)
    output_bit_2 = digital_outputs.add_variable(idx, "ur10e output bit 2", False)
    output_bit_3 = digital_outputs.add_variable(idx, "ur10e output bit 3", False)
    output_bit_4 = digital_outputs.add_variable(idx, "ur10e output bit 4", False)
    output_bit_5 = digital_outputs.add_variable(idx, "ur10e output bit 5", False)
    output_bit_6 = digital_outputs.add_variable(idx, "ur10e output bit 6", False)
    output_bit_7 = digital_outputs.add_variable(idx, "ur10e output bit 7", False)
    output_bit_0.set_writable()
    output_bit_1.set_writable()
    output_bit_2.set_writable()
    output_bit_3.set_writable()
    output_bit_4.set_writable()
    output_bit_5.set_writable()
    output_bit_6.set_writable()
    output_bit_7.set_writable()

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
        target_joint_positions,

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
        target_TCP_positions,

        move_type,
        home_position,
        joint_speed,
        joint_acceleration,
        tcp_speed,
        tcp_acceleration,
        moving_flag,

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
        output_bit_7
    ]
    return dataset
