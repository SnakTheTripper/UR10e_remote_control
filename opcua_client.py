import asyncio
import config
from datetime import datetime
from asyncua import Client

opcua_period = 1000 / config.opcua_frequency


class SubHandler:
    def __init__(self):
        self.prev_time = datetime.now()

    async def datachange_notification(self, node, value, data):
        current_time = datetime.now()
        delta_time = (current_time - self.prev_time).total_seconds()

        if delta_time > 0:  # Avoid division by zero
            frequency = 1 / delta_time
            print(f"Frequency: {frequency:.2f} Hz - Updated! Node: {node}, Value: {value}")

        self.prev_time = current_time

async def main():
    full_path = f"opc.tcp://{config.ip_address_opcua_server}:{config.port_opcua}"
    # instantiate and connect client
    client = Client(url=full_path)
    try:
        await client.connect()

        # Get the root object from which you can navigate
        root = client.nodes.root

        # Navigate through folders and objects to get to your variables
        ur10e_folder = await root.get_child(["0:Objects", "2:ur10e Platform"])
        ur10e_current_joint = await ur10e_folder.get_child(["2:1 ur10e Current Joint"])

        # Create subscription and define handler
        sub = await client.create_subscription(opcua_period, SubHandler())

        current_joint_1 = await ur10e_current_joint.get_child(["2:ur10e A1 Current"])
        current_joint_2 = await ur10e_current_joint.get_child(["2:ur10e A2 Current"])
        current_joint_3 = await ur10e_current_joint.get_child(["2:ur10e A3 Current"])
        current_joint_4 = await ur10e_current_joint.get_child(["2:ur10e A4 Current"])
        current_joint_5 = await ur10e_current_joint.get_child(["2:ur10e A5 Current"])
        # Add more variables as needed

        await sub.subscribe_data_change(current_joint_1)
        # await sub.subscribe_data_change(current_joint_2)
        # await sub.subscribe_data_change(current_joint_3)
        # await sub.subscribe_data_change(current_joint_4)
        # await sub.subscribe_data_change(current_joint_5)
        # Add more subscriptions as needed

        while True:
            await asyncio.sleep(10)

    except:
        print('exception!')
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
