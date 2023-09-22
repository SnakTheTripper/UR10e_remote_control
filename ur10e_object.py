async def ur10e_platform_variables(addspace, node):

    ur10e_obj = await node.add_folder(addspace, "ur10e Platform")

    ur10e_current_joint = await ur10e_obj.add_object(addspace, "1 ur10e Current Joint")
    ur10e_A1_current = await ur10e_current_joint.add_variable(addspace, "ur10e A1 Current", 0.0)
    ur10e_A2_current = await ur10e_current_joint.add_variable(addspace, "ur10e A2 Current", -90.0)
    ur10e_A3_current = await ur10e_current_joint.add_variable(addspace, "ur10e A3 Current", 0.0)
    ur10e_A4_current = await ur10e_current_joint.add_variable(addspace, "ur10e A4 Current", -90.0)
    ur10e_A5_current = await ur10e_current_joint.add_variable(addspace, "ur10e A5 Current", 0.0)
    ur10e_A6_current = await ur10e_current_joint.add_variable(addspace, "ur10e A6 Current", 0.0)
    await ur10e_A1_current.set_writable()
    await ur10e_A2_current.set_writable()
    await ur10e_A3_current.set_writable()
    await ur10e_A4_current.set_writable()
    await ur10e_A5_current.set_writable()
    await ur10e_A6_current.set_writable()

    ur10e_wanted_joint = await ur10e_obj.add_object(addspace, "2 ur10e Target Joint")
    ur10e_A1_wanted = await ur10e_wanted_joint.add_variable(addspace, "ur10e A1 Target", 0.0)
    ur10e_A2_wanted = await ur10e_wanted_joint.add_variable(addspace, "ur10e A2 Target", -90.0)
    ur10e_A3_wanted = await ur10e_wanted_joint.add_variable(addspace, "ur10e A3 Target", 0.0)
    ur10e_A4_wanted = await ur10e_wanted_joint.add_variable(addspace, "ur10e A4 Target", -90.0)
    ur10e_A5_wanted = await ur10e_wanted_joint.add_variable(addspace, "ur10e A5 Target", 0.0)
    ur10e_A6_wanted = await ur10e_wanted_joint.add_variable(addspace, "ur10e A6 Target", 0.0)
    ur10e_wanted_joint_positions = await ur10e_wanted_joint.add_variable(addspace, "ur10e Target Joint Positions", "{}")
    await ur10e_A1_wanted.set_writable()
    await ur10e_A2_wanted.set_writable()
    await ur10e_A3_wanted.set_writable()
    await ur10e_A4_wanted.set_writable()
    await ur10e_A5_wanted.set_writable()
    await ur10e_A6_wanted.set_writable()
    await ur10e_wanted_joint_positions.set_writable()

    ur10e_current_xyz = await ur10e_obj.add_object(addspace, "3 ur10e Current xyz")
    ur10e_x_current = await ur10e_current_xyz.add_variable(addspace, "ur10e x Current", 0.45)
    ur10e_y_current = await ur10e_current_xyz.add_variable(addspace, "ur10e y Current", 0.0)
    ur10e_z_current = await ur10e_current_xyz.add_variable(addspace, "ur10e z Current", 0.7)
    ur10e_rx_current = await ur10e_current_xyz.add_variable(addspace, "ur10e rx Current", 0.0)
    ur10e_ry_current = await ur10e_current_xyz.add_variable(addspace, "ur10e ry Current", 0.0)
    ur10e_rz_current = await ur10e_current_xyz.add_variable(addspace, "ur10e rz Current", 0.0)
    await ur10e_x_current.set_writable()
    await ur10e_y_current.set_writable()
    await ur10e_z_current.set_writable()
    await ur10e_rx_current.set_writable()
    await ur10e_ry_current.set_writable()
    await ur10e_rz_current.set_writable()

    ur10e_wanted_xyz = await ur10e_obj.add_object(addspace, "4 ur10e Wanted xyz")
    ur10e_x_wanted = await ur10e_wanted_xyz.add_variable(addspace, "ur10e x Wanted", 0.45)
    ur10e_y_wanted = await ur10e_wanted_xyz.add_variable(addspace, "ur10e y Wanted", 0.0)
    ur10e_z_wanted = await ur10e_wanted_xyz.add_variable(addspace, "ur10e z Wanted", 0.7)
    ur10e_rx_wanted = await ur10e_wanted_xyz.add_variable(addspace, "ur10e rx Wanted", 0.0)
    ur10e_ry_wanted = await ur10e_wanted_xyz.add_variable(addspace, "ur10e ry Wanted", 0.0)
    ur10e_rz_wanted = await ur10e_wanted_xyz.add_variable(addspace, "ur10e rz Wanted", 0.0)
    ur10e_wanted_TCP_positions = await ur10e_wanted_xyz.add_variable(addspace, "ur10e Wanted TCP Positions", "{}")
    await ur10e_x_wanted.set_writable()
    await ur10e_y_wanted.set_writable()
    await ur10e_z_wanted.set_writable()
    await ur10e_rx_wanted.set_writable()
    await ur10e_ry_wanted.set_writable()
    await ur10e_rz_wanted.set_writable()
    await ur10e_wanted_TCP_positions.set_writable()

    ur10e_control = await ur10e_obj.add_object(addspace, "5 ur10e Control")
    ur10e_wanted_pos_format = await ur10e_control.add_variable(addspace, "ur10e Wanted Position Format", 0.0)
    ur10e_home_position = await ur10e_control.add_variable(addspace, "ur10e Home Position", 0.0)
    ur10e_joint_speed = await ur10e_control.add_variable(addspace, "ur10e Joint Speed", 0.1)
    ur10e_joint_acceleration = await ur10e_control.add_variable(addspace, "ur10e Joint Acceleration", 0.1)
    ur10e_tcp_speed = await ur10e_control.add_variable(addspace, "ur10e TCP Speed", 0.0)
    ur10e_tcp_acceleration = await ur10e_control.add_variable(addspace, "ur10e TCP Acceleration", 0.0)
    ur10e_moving_flag = await ur10e_control.add_variable(addspace, "ur10e Moving Flag", 0.0)
    await ur10e_wanted_pos_format.set_writable()
    await ur10e_home_position.set_writable()
    await ur10e_joint_speed.set_writable()
    await ur10e_joint_acceleration.set_writable()
    await ur10e_tcp_speed.set_writable()
    await ur10e_tcp_acceleration.set_writable()
    await ur10e_moving_flag.set_writable()

    ur10e_digital_inputs = await ur10e_obj.add_object(addspace, "8 ur10e Digital Input bits")
    ur10e_input_bit_0 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 0", False)
    ur10e_input_bit_1 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 1", False)
    ur10e_input_bit_2 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 2", False)
    ur10e_input_bit_3 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 3", False)
    ur10e_input_bit_4 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 4", False)
    ur10e_input_bit_5 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 5", False)
    ur10e_input_bit_6 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 6", False)
    ur10e_input_bit_7 = await ur10e_digital_inputs.add_variable(addspace, "ur10e input bit 7", False)
    await ur10e_input_bit_0.set_writable()
    await ur10e_input_bit_1.set_writable()
    await ur10e_input_bit_2.set_writable()
    await ur10e_input_bit_3.set_writable()
    await ur10e_input_bit_4.set_writable()
    await ur10e_input_bit_5.set_writable()
    await ur10e_input_bit_6.set_writable()
    await ur10e_input_bit_7.set_writable()

    ur10e_digital_outputs = await ur10e_obj.add_object(addspace, "8 ur10e Digital Output bits")
    ur10e_output_bit_0 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 0", False)
    ur10e_output_bit_1 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 1", False)
    ur10e_output_bit_2 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 2", False)
    ur10e_output_bit_3 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 3", False)
    ur10e_output_bit_4 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 4", False)
    ur10e_output_bit_5 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 5", False)
    ur10e_output_bit_6 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 6", False)
    ur10e_output_bit_7 = await ur10e_digital_outputs.add_variable(addspace, "ur10e output bit 7", False)
    await ur10e_output_bit_0.set_writable()
    await ur10e_output_bit_1.set_writable()
    await ur10e_output_bit_2.set_writable()
    await ur10e_output_bit_3.set_writable()
    await ur10e_output_bit_4.set_writable()
    await ur10e_output_bit_5.set_writable()
    await ur10e_output_bit_6.set_writable()
    await ur10e_output_bit_7.set_writable()

    dataset = [
        ur10e_A1_current,
        ur10e_A2_current,
        ur10e_A3_current,
        ur10e_A4_current,
        ur10e_A5_current,
        ur10e_A6_current,

        ur10e_A1_wanted,
        ur10e_A2_wanted,
        ur10e_A3_wanted,
        ur10e_A4_wanted,
        ur10e_A5_wanted,
        ur10e_A6_wanted,
        ur10e_wanted_joint_positions,

        ur10e_x_current,
        ur10e_y_current,
        ur10e_z_current,
        ur10e_rx_current,
        ur10e_ry_current,
        ur10e_rz_current,

        ur10e_x_wanted,
        ur10e_y_wanted,
        ur10e_z_wanted,
        ur10e_rx_wanted,
        ur10e_ry_wanted,
        ur10e_rz_wanted,
        ur10e_wanted_TCP_positions,

        ur10e_wanted_pos_format,
        ur10e_home_position,
        ur10e_joint_speed,
        ur10e_joint_acceleration,
        ur10e_tcp_speed,
        ur10e_tcp_acceleration,
        ur10e_moving_flag,

        ur10e_input_bit_0,
        ur10e_input_bit_1,
        ur10e_input_bit_2,
        ur10e_input_bit_3,
        ur10e_input_bit_4,
        ur10e_input_bit_5,
        ur10e_input_bit_6,
        ur10e_input_bit_7,

        ur10e_output_bit_0,
        ur10e_output_bit_1,
        ur10e_output_bit_2,
        ur10e_output_bit_3,
        ur10e_output_bit_4,
        ur10e_output_bit_5,
        ur10e_output_bit_6,
        ur10e_output_bit_7
    ]
    return (
        dataset)
