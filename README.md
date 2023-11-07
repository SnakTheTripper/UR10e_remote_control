# UR10e_remote_control

remote control application for UR10e robot with ZMQ communication between Flask server and robot controller using RTDE.

## Getting started
For the python script we use a virtual environment that contains all the necesarry dependencies as described by the requirements file.  
Tested on Linux Mint, Ubuntu 22.04 (?) and WSL.

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
* **videos**: contains the video feed containers for the different camera feeds
  
**ur10e_programs**:

**programs.py**: contains predefined targets to test the **Run Program** functionality of the control pages with sequential *moveJ* and *moveL* instructions.

**Flask_server.py**: website generation and user event handling stript. Forwards user inputs from the webpage to the **MiddleWare** in the form of target positions, can also control IO (when Control Mode is set to Flask). The robot's current positions and IO states are updated with a configurable frequency (*FLASK_FREQ* in *config.py*).

**MWare.py**: async managment of FlaskHandler & OpcuaHandler to realize communication between those servers and the UR10e_bridge.py. It also handles the control switching function between Flask and Opcua with the appropriate logic for keeping everything up to date.

**config.py**: contains TCP/IP configuration values for the robot access, cammera link and cloud ports. It also contains data rate values for the rtde interface.

**opcua_server.py**: mirrors current robot state including IO. Also capable of sending target position to move the robot when the *control_mode* is set to *1* (OPCUA mode). Update frequency is configurable in *config.py* (*OPCUA_FREQ*). Can be used to simulate the robot in virtual space (eg. Visual Components) or to controll it with any module connected to the OPCUA interface.

**project_utils.py**: unit conversion functions for other modules.

**requiremments.txt**: contains the python library requirements for the whole project (both for the cloud-based server and for the local bridge).

**ur10e_bridge.py**: represents the bridge between UR10e robot and MiddleWare. It uses RTDE Receive, RTDE Control, RTDE IO and Dashboard Client APIs to receive current data and to send move commands to the robot. It also contains a ZMQ interface that is used to transmit data between it and MiddleWare. MW is always kept up to date with *RTDE_FREQ* (*config.py*)

**ur10e_object.py**: used to populate the OPCUA Server with UR10e object and all the relevant nodes, while also creating a python object with variables for all OPCUA nodes. Contains reference and current values for the UR10e joint variables, end effector displacement and orientation, movement speed, movement acceleration and digital I/O etc.

## Running the program

```diff
(all .py modules can be run from one machines)

@@ TODO: @@

Setting up config.py:
- ONLINE_MODE = True if Flask_server.py is running on cloud machine, False if running on local network

- set the appropriate ip addresses: 
  - IP_UR10e = robot's IP on local network. Can be substituted by URSim running UR10e controller software.
  - IP_BRIDGE = IP of machine running ur10e_bridge.py
  - IP_MWARE = IP of machine running MWare.py
  - IP_OPCUA = IP of machine running opcua_server.py
  - IP_FLASK_LOCAL = IP of machine running Flask_server.py on local network (if ONLINE_MODE = False)
  - IP_FLASK_CLOUD = public IP of the cloud machine running Flask_server.py (if ONLINE_MODE = True)

- set up the appropriate ports for Flask Server, OPCUA Server and ZMQ communication

- set desired Update Frequencies

- select default Control Mode (which module will be able to send move commands to the robot)

- set robot Home Position and Joint Limits

- set network camera's RTSP links (max 3)

- optionally set a starter program to be loaded on Flask Server start
```
