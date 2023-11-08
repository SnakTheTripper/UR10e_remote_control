# UR10e_remote_control

remote control application for UR10e robot with ZMQ communication between Flask server and robot controller using RTDE.

Attention: Remote Control needs to be enabled on robot controller for this software package to work!

## Getting started
For the python script we use a virtual environment that contains all the necesarry dependencies as described by the requirements file.  
Tested on Linux Mint, Ubuntu 22.04 and WSL.

To create and activate a virtual environment, you will need to run the following commands:  
`$ python3 -m venv .env`

To activate and use the virtual environment:  
`source .env/bin/activate`

Notice the (.env)!    
As long as this is active any package will be installed in this virtual environment, rather than globally. 

## Project structure

**\_\_pycache\_\_**: Contains precompiled python modules. Will be removed in future updates using gitignore.

**static**: Contains static images used for the website.


**templates**: Contains the website static templates:
* *home.html*: Home page with HTML and CSS combined 
* *JOINT_control.html*: the P2P operation website of the robot using joint space control 
* *TCP_control.html*: the linear motion website of the robot using end effector space control
* **videos**: contains the video feed containers for the camera feeds
  
**UR10e Programs**:

* **ur10e_bridge.py**: represents the bridge between UR10e robot and MiddleWare. It uses RTDE Receive, RTDE Control, RTDE IO and Dashboard Client APIs to receive current data and to send move commands to the robot. It also contains a ZMQ interface that is used to transmit data between it and MiddleWare. MW is always kept up to date with *RTDE_FREQ* (*config.py*)

* **MWare.py**: MiddleWare module for async managment of FlaskHandler & OpcuaHandler to realize communication between those servers and the UR10e_bridge.py. It also handles the control switching function between Flask and Opcua with the appropriate logic for keeping everything up to date.

* **Flask_server.py**: website generation and user event handling stript. Forwards user inputs from the webpage to the **MiddleWare** in the form of target positions, can also control IO (when Control Mode is set to Flask). The robot's current positions and IO states are updated with a configurable frequency (*FLASK_FREQ* in *config.py*).

* **opcua_server.py**: mirrors current robot state including IO. Also capable of sending target position to move the robot when the *control_mode* is set to *1* (OPCUA mode). Update frequency is configurable in *config.py* (*OPCUA_FREQ*). Can be used to simulate the robot in virtual space (eg. Visual Components) or to controll it with any module connected to the OPCUA interface.

* **ur10e_object.py**: used to populate the OPCUA Server with UR10e object and all the relevant nodes, while also creating a python object with variables for all OPCUA nodes. Contains reference and current values for the UR10e joint variables, end effector displacement and orientation, movement speed, movement acceleration and digital I/O etc.

* **config.py**: contains TCP/IP configuration values for the robot access, cammera link and cloud ports. It also contains data rate values for the rtde interface.

* **project_utils.py**: unit conversion functions for other modules.

* **requiremments.txt**: contains the python library requirements for the whole project (both for the cloud-based server and for the local bridge).

## Running the program

IP adresses of host machines need to be set to static!
How-to:
* Windows: https://kb.netgear.com/27476/How-do-I-set-a-static-IP-address-in-Windows
* Linux: https://www.freecodecamp.org/news/setting-a-static-ip-in-ubuntu-linux-ip-address-tutorial/

```diff
# Configuration Instructions

Proper setup of `config.py` is essential for seamless communication across the system components.
Follow these guidelines to ensure correct configuration.

## Mode Selection
Set the operational environment:
- `ONLINE_MODE`: `True` for cloud-hosted `Flask_server.py`; `False` for local network operation.

## IP Addresses Setup
Assign appropriate IP addresses to each component:
- `IP_UR10e`: IP of UR10e robot or URSim.
- `IP_BRIDGE`: IP of `ur10e_bridge.py` host.
- `IP_MWARE`: IP of `Mware.py` host.
- `IP_OPCUA`: IP of `opcua_server.py` host.
- `IP_FLASK_LOCAL`: Local IP for `Flask_server.py` (if `ONLINE_MODE` is `False`).
- `IP_FLASK_CLOUD`: Cloud machine's public IP (if `ONLINE_MODE` is `True`).

## Port Configuration
Define communication ports and verify firewall permissions:
- Flask Server port
- OPCUA Server port
- ZMQ communication port

## Update Frequency
Set refresh rates for each component's data updates.

## Control Mode
Select the initial control module (`FLASK` or `OPCUA`) for robot move commands.

## Robot Settings
Specify the robot's "Home" position and joint limits for safety.

## Network Cameras
Include RTSP links for network cameras, supporting up to 3.

## Optional Starter Program
Option to load a starter program on Flask Server launch.

Ensure all settings are verified for the system to function correctly.

## Module Start Sequence
Execute the following modules in any order:
- `ur10e_bridge.py`
- `MWare.py`
- `opcua_server.py`
- `Flask_server.py`

Check terminal output for potential errors related to Ports or IP configurations.

```
