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
  
**ur10e_programs**: *demo.py*: and *programs.py* contain predefined targets to test the **moveJ** and **moveL** instructions.

*Flask_server.py*: website generation and user event handling stript.

*MWare.py*: async management of the opcua client, zmq handler, flask executioner and local ur_rtde.

*config.py*: contains TCP/IP configuration values for the robot access, cammera link and cloud ports. It also contains data rate values for the rtde interface.

*opcua_server.py*: serves the robot states to opcua-based monitoring system such as ...

*project_utils.py*: usefull unit conversion functions.

*requiremments.txt*: contains the python library requirements for the whole project (both for the cloud-based server and for the local bridge).

*ur10e_bridge.py*: robot-side data manager with zmq interface. Uses the *ur_rtde* library to get info from the robot and send commands to it.

*ur10e_object.py*: Desines the OPCUA objects to successfully decipher the data to and from the server. Contains reference and current values for the UR10e joint variables, end effector displacement and orientation, movement speed, movement acceleration and logic I/O.

## Running the program

```diff
@@ TODO: @@
- Ide le kell irni a program futtatasanak eljarasat... 
- pl. kell egy lokalis gep amin fut az bridge...
- kell egy cloud szerver amin ki kell nyitni XXX portot, ezt a portot be kell irni a lokalis config.py allomanyba
- a cloud-on kell futatni a flask programot es az opcua szervert
```
