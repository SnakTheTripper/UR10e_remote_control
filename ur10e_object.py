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

    ur10e_target_xyz = ur10e_obj.add_object(idx, "4 UR10e Target TCP")
    target_x = ur10e_target_xyz.add_variable(idx, "Target x", 0.45)
    target_y = ur10e_target_xyz.add_variable(idx, "Target y", 0.0)
    target_z = ur10e_target_xyz.add_variable(idx, "Target z", 0.7)
    target_roll = ur10e_target_xyz.add_variable(idx, "Target Roll", 0.0)
    target_pitch = ur10e_target_xyz.add_variable(idx, "Target Pitch", 0.0)
    target_yaw = ur10e_target_xyz.add_variable(idx, "Target Yaw", 0.0)
    target_x.set_writable()
    target_y.set_writable()
    target_z.set_writable()
    target_roll.set_writable()
    target_pitch.set_writable()
    target_yaw.set_writable()

    control = ur10e_obj.add_object(idx, "5 UR10e Control Values")

    move_type = control.add_variable(idx, "move_type", 1)  # 0 - linear, 1 - joint
    control_mode = control.add_variable(idx, "control_mode", config.DEFAULT_CONTROL_MODE)  # 0 - flask,  1 - opcua
    joint_speed = control.add_variable(idx, "Joint Speed", 10)
    joint_accel = control.add_variable(idx, "Joint Acceleration", 10)
    tcp_speed = control.add_variable(idx, "TCP Speed", 0.1)
    tcp_accel = control.add_variable(idx, "TCP Acceleration", 0.1)
    is_moving = control.add_variable(idx, "is_moving", 0)
    STOP = control.add_variable(idx, "STOP", 0)
    move_type.set_writable()  # 0 = linear 1 = joint
    control_mode.set_writable()
    joint_speed.set_writable()
    joint_accel.set_writable()
    tcp_speed.set_writable()
    tcp_accel.set_writable()
    is_moving.set_writable()
    STOP.set_writable()

    # I/O STATUS & CONTROL

    # CURRENT INPUT

    digital_inputs = ur10e_obj.add_object(idx, "6 UR10e Digital Input bits")
    standard_input_bit_0 = digital_inputs.add_variable(idx, "Standard Input bit 0", 0)
    standard_input_bit_1 = digital_inputs.add_variable(idx, "Standard Input bit 1", 0)
    standard_input_bit_2 = digital_inputs.add_variable(idx, "Standard Input bit 2", 0)
    standard_input_bit_3 = digital_inputs.add_variable(idx, "Standard Input bit 3", 0)
    standard_input_bit_4 = digital_inputs.add_variable(idx, "Standard Input bit 4", 0)
    standard_input_bit_5 = digital_inputs.add_variable(idx, "Standard Input bit 5", 0)
    standard_input_bit_6 = digital_inputs.add_variable(idx, "Standard Input bit 6", 0)
    standard_input_bit_7 = digital_inputs.add_variable(idx, "Standard Input bit 7", 0)

    configurable_input_bit_0 = digital_inputs.add_variable(idx, "Configurable Input bit 0", 0)
    configurable_input_bit_1 = digital_inputs.add_variable(idx, "Configurable Input bit 1", 0)
    configurable_input_bit_2 = digital_inputs.add_variable(idx, "Configurable Input bit 2", 0)
    configurable_input_bit_3 = digital_inputs.add_variable(idx, "Configurable Input bit 3", 0)
    configurable_input_bit_4 = digital_inputs.add_variable(idx, "Configurable Input bit 4", 0)
    configurable_input_bit_5 = digital_inputs.add_variable(idx, "Configurable Input bit 5", 0)
    configurable_input_bit_6 = digital_inputs.add_variable(idx, "Configurable Input bit 6", 0)
    configurable_input_bit_7 = digital_inputs.add_variable(idx, "Configurable Input bit 7", 0)

    tool_input_bit_6 = digital_inputs.add_variable(idx, "Tool Input bit 6", 0)
    tool_input_bit_7 = digital_inputs.add_variable(idx, "Tool Input bit 7", 0)

    # CURRENT OUTPUT

    digital_outputs = ur10e_obj.add_object(idx, "7 ur10e Digital Output bits")
    standard_output_bit_0 = digital_outputs.add_variable(idx, "Standard Output bit 0", 0)
    standard_output_bit_1 = digital_outputs.add_variable(idx, "Standard Output bit 1", 0)
    standard_output_bit_2 = digital_outputs.add_variable(idx, "Standard Output bit 2", 0)
    standard_output_bit_3 = digital_outputs.add_variable(idx, "Standard Output bit 3", 0)
    standard_output_bit_4 = digital_outputs.add_variable(idx, "Standard Output bit 4", 0)
    standard_output_bit_5 = digital_outputs.add_variable(idx, "Standard Output bit 5", 0)
    standard_output_bit_6 = digital_outputs.add_variable(idx, "Standard Output bit 6", 0)
    standard_output_bit_7 = digital_outputs.add_variable(idx, "Standard Output bit 7", 0)

    configurable_output_bit_0 = digital_outputs.add_variable(idx, "Configurable Output bit 0", 0)
    configurable_output_bit_1 = digital_outputs.add_variable(idx, "Configurable Output bit 1", 0)
    configurable_output_bit_2 = digital_outputs.add_variable(idx, "Configurable Output bit 2", 0)
    configurable_output_bit_3 = digital_outputs.add_variable(idx, "Configurable Output bit 3", 0)
    configurable_output_bit_4 = digital_outputs.add_variable(idx, "Configurable Output bit 4", 0)
    configurable_output_bit_5 = digital_outputs.add_variable(idx, "Configurable Output bit 5", 0)
    configurable_output_bit_6 = digital_outputs.add_variable(idx, "Configurable Output bit 6", 0)
    configurable_output_bit_7 = digital_outputs.add_variable(idx, "Configurable Output bit 7", 0)

    tool_output_bit_6 = digital_outputs.add_variable(idx, "Tool Output bit 6", 0)
    tool_output_bit_7 = digital_outputs.add_variable(idx, "Tool Output bit 7", 0)

    # TARGET OUTPUT

    target_standard_output_bit_0 = digital_outputs.add_variable(idx, "Target Standard Output bit 0", 0)
    target_standard_output_bit_1 = digital_outputs.add_variable(idx, "Target Standard Output bit 1", 0)
    target_standard_output_bit_2 = digital_outputs.add_variable(idx, "Target Standard Output bit 2", 0)
    target_standard_output_bit_3 = digital_outputs.add_variable(idx, "Target Standard Output bit 3", 0)
    target_standard_output_bit_4 = digital_outputs.add_variable(idx, "Target Standard Output bit 4", 0)
    target_standard_output_bit_5 = digital_outputs.add_variable(idx, "Target Standard Output bit 5", 0)
    target_standard_output_bit_6 = digital_outputs.add_variable(idx, "Target Standard Output bit 6", 0)
    target_standard_output_bit_7 = digital_outputs.add_variable(idx, "Target Standard Output bit 7", 0)

    target_configurable_output_bit_0 = digital_outputs.add_variable(idx, "Target Configurable Output bit 0", 0)
    target_configurable_output_bit_1 = digital_outputs.add_variable(idx, "Target Configurable Output bit 1", 0)
    target_configurable_output_bit_2 = digital_outputs.add_variable(idx, "Target Configurable Output bit 2", 0)
    target_configurable_output_bit_3 = digital_outputs.add_variable(idx, "Target Configurable Output bit 3", 0)
    target_configurable_output_bit_4 = digital_outputs.add_variable(idx, "Target Configurable Output bit 4", 0)
    target_configurable_output_bit_5 = digital_outputs.add_variable(idx, "Target Configurable Output bit 5", 0)
    target_configurable_output_bit_6 = digital_outputs.add_variable(idx, "Target Configurable Output bit 6", 0)
    target_configurable_output_bit_7 = digital_outputs.add_variable(idx, "Target Configurable Output bit 7", 0)

    target_tool_output_bit_0 = digital_outputs.add_variable(idx, "Target Tool Output bit 0", 0)
    target_tool_output_bit_1 = digital_outputs.add_variable(idx, "Target Tool Output bit 1", 0)

    target_standard_output_bit_0.set_writable()
    target_standard_output_bit_1.set_writable()
    target_standard_output_bit_2.set_writable()
    target_standard_output_bit_3.set_writable()
    target_standard_output_bit_4.set_writable()
    target_standard_output_bit_5.set_writable()
    target_standard_output_bit_6.set_writable()
    target_standard_output_bit_7.set_writable()

    target_configurable_output_bit_0.set_writable()
    target_configurable_output_bit_1.set_writable()
    target_configurable_output_bit_2.set_writable()
    target_configurable_output_bit_3.set_writable()
    target_configurable_output_bit_4.set_writable()
    target_configurable_output_bit_5.set_writable()
    target_configurable_output_bit_6.set_writable()
    target_configurable_output_bit_7.set_writable()

    target_tool_output_bit_0.set_writable()
    target_tool_output_bit_1.set_writable()

    SEND_MOVEMENT = ur10e_obj.add_variable(idx, "8 SEND MOVEMENT", 0)  # send target values to MW when set to 1
    SEND_MOVEMENT.set_writable()
    SEND_OUTPUT_BITS = ur10e_obj.add_variable(idx, "9 SEND OUTPUT BITS", 0)  # send digital output bits to MW
    SEND_OUTPUT_BITS.set_writable()

    # DO NOT CHANGE THE ORDER
    # ANY ADDITION IS TO BE MADE TO THE END OF THE LIST
    # opcua_server.py uses 'browse_names_to_var' dictionary to identify elements of the opcua dataset by name
    # if the order changes, everything breaks. Modify with caution!
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
        target_roll,
        target_pitch,
        target_yaw,

        move_type,
        control_mode,
        joint_speed,
        joint_accel,
        tcp_speed,
        tcp_accel,
        is_moving,

        # standard input bits
        [standard_input_bit_0,
         standard_input_bit_1,
         standard_input_bit_2,
         standard_input_bit_3,
         standard_input_bit_4,
         standard_input_bit_5,
         standard_input_bit_6,
         standard_input_bit_7],
        # configurable input bits
        [configurable_input_bit_0,
         configurable_input_bit_1,
         configurable_input_bit_2,
         configurable_input_bit_3,
         configurable_input_bit_4,
         configurable_input_bit_5,
         configurable_input_bit_6,
         configurable_input_bit_7],
        # tool input bits
        [tool_input_bit_6,
         tool_input_bit_7],

        # standard output bits
        [standard_output_bit_0,
         standard_output_bit_1,
         standard_output_bit_2,
         standard_output_bit_3,
         standard_output_bit_4,
         standard_output_bit_5,
         standard_output_bit_6,
         standard_output_bit_7],
        # configurable output bits
        [configurable_output_bit_0,
         configurable_output_bit_1,
         configurable_output_bit_2,
         configurable_output_bit_3,
         configurable_output_bit_4,
         configurable_output_bit_5,
         configurable_output_bit_6,
         configurable_output_bit_7],
        # tool output bits
        [tool_output_bit_6,
         tool_output_bit_7],

        # target standard output bits
        [target_standard_output_bit_0,
         target_standard_output_bit_1,
         target_standard_output_bit_2,
         target_standard_output_bit_3,
         target_standard_output_bit_4,
         target_standard_output_bit_5,
         target_standard_output_bit_6,
         target_standard_output_bit_7],
        # target configurable output bits
        [target_configurable_output_bit_0,
         target_configurable_output_bit_1,
         target_configurable_output_bit_2,
         target_configurable_output_bit_3,
         target_configurable_output_bit_4,
         target_configurable_output_bit_5,
         target_configurable_output_bit_6,
         target_configurable_output_bit_7],
        # target tool output bits
        [target_tool_output_bit_0,
         target_tool_output_bit_1],

        SEND_MOVEMENT,
        SEND_OUTPUT_BITS,
        STOP
    ]
    # DO NOT CHANGE THE ORDER
    # ANY ADDITION IS TO BE MADE TO THE END OF THE LIST
    # opcua_server.py uses 'browse_names_to_var' dictionary to identify elements of the opcua dataset by name
    # if the order changes, everything breaks. Modify with caution!
    return dataset
