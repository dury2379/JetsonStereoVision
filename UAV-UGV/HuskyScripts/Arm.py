#!/usr/bin/python
import socket
import time
import roslib
roslib.load_manifest('robotiq_3f_gripper_control')
import rospy
from robotiq_3f_gripper_msgs.msg import SModelRobotOutput
from time import sleep

def genCommand(char, command):
    """Update the command according to the character entered by the user."""

    if char == 'a':
        command = SModelRobotOutput()
        command.rACT = 1
        command.rGTO = 1
        command.rSPA = 255
        command.rFRA = 150

    if char == 'r':
        command = SModelRobotOutput()
        command.rACT = 0

    if char == 'c':
        command.rPRA = 255

    if char == 'o':
        command.rPRA = 0

    if char == 'b':
        command.rMOD = 0

    if char == 'p':
        command.rMOD = 1

    if char == 'w':
        command.rMOD = 2

    if char == 's':
        command.rMOD = 3

    # If the command entered is an int, assign this value to rPRA
    try:
        command.rPRA = int(char)
        if command.rPRA > 255:
            command.rPRA = 255
        if command.rPRA < 0:
            command.rPRA = 0
    except ValueError:
        pass

    if char == 'f':
        command.rSPA += 25
        if command.rSPA > 255:
            command.rSPA = 255

    if char == 'l':
        command.rSPA -= 25
        if command.rSPA < 0:
            command.rSPA = 0

    if char == 'i':
        command.rFRA += 25
        if command.rFRA > 255:
            command.rFRA = 255

    if char == 'd':
        command.rFRA -= 25
        if command.rFRA < 0:
            command.rFRA = 0

    return command

def publisher(tup, t):
    """Main loop which sends a predefined sequence of commands."""

    rospy.init_node('SModelSimpleController')

    topic_name = rospy.get_param('~topic', 'SModelRobotOutput')
    pub = rospy.Publisher(topic_name, SModelRobotOutput, queue_size=10)

    command = SModelRobotOutput()

    # Define the sequence of commands
    command_sequence = tup

    for cmd in command_sequence:
        command = genCommand(cmd, command)
        pub.publish(command)
        rospy.loginfo('Published command: {}'.format(cmd))
        sleep(t)  # Sleep for 10 second between commands

    rospy.loginfo('Command sequence completed.')

# Define the UR script to be sent
ur_script_1 = """
def move_to_waypoints():
  global Waypoint_1_p=p[-.138684209690, -.209774642415, .163512782515, 2.418936792721, .626193470986, -.231201842463]
  global Waypoint_1_q=[-1.5979397932635706, -0.2707976859859009, -2.8107638359069824, -0.9735104602626343, 1.578035831451416, 2.6078264713287354]
  global Waypoint_2_p=p[.006277621834, -.655574000100, -.241375281222, -1.565138491659, -1.403265367244, 2.130659848597]
  global Waypoint_2_q=[-0.9386184851275843, -3.267109533349508, -1.3970122337341309, 0.3282267290302734, -0.020647827778951466, 1.929986834526062]
  $ 1 "Robot Program"
  $ 2 "MoveJ"
  $ 3 "Waypoint_1" "breakAfter"
  movej(get_inverse_kin(Waypoint_1_p, qnear=Waypoint_1_q), a=1.3962634015954636, v=1.0471975511965976)
  $ 4 "Waypoint_2" "breakAfter"
  movej(get_inverse_kin(Waypoint_2_p, qnear=Waypoint_2_q), a=1.3962634015954636, v=1.0471975511965976)
  $ 5 "Halt"
  halt
end
move_to_waypoints()
"""
ur_script_2 = """
def move_to_waypoints_1():
  global Waypoint_1_p=p[.006252063458, -.655568467956, -.241384251880, -1.565123883144, -1.403265773446, 2.130610608919]
  global Waypoint_1_q=[-0.9386509100543421, -3.267113824883932, -1.3970328569412231, 0.32821957647290034, -0.02063161531557256, 1.9299836158752441]
  global Waypoint_2_p=p[-.138690792424, -.209766350896, .163487440335, 2.419014918936, .626185710129, -.231205883372]
  global Waypoint_2_q=[-1.5979488531695765, -0.2708140176585694, -2.8107872009277344, -0.9735419315150757, 1.5780164003372192, 2.607832193374634]
  while (True):
    $ 1 "Robot Program"
    $ 2 "MoveJ"
    $ 3 "Waypoint_1" "breakAfter"
    movej(get_inverse_kin(Waypoint_1_p, qnear=Waypoint_1_q), a=1.3962634015954636, v=1.0471975511965976)
    $ 4 "Waypoint_2" "breakAfter"
    movej(get_inverse_kin(Waypoint_2_p, qnear=Waypoint_2_q), a=1.3962634015954636, v=1.0471975511965976)
    $ 5 "Halt"
    halt
  end
end
move_to_waypoints_1()
"""
def soc1():
        # Define UR controller IP address and port
        UR_IP = "192.168.131.40"  # Replace with your UR controller IP address
        UR_PORT = 30002  # Default URScript port

        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to UR controller
        sock.connect((UR_IP, UR_PORT))
        print "Connected to UR controller at {}:{}".format(UR_IP, UR_PORT)
        return sock
def Arm1(sock):
        # Send UR script command
        sock.sendall(ur_script_1)

        # Add a delay to ensure the script is executed
        time.sleep(5)
def Arm2(sock):
        # Send UR script command
        sock.sendall(ur_script_2)

        # Add a delay to ensure the script is executed
        time.sleep(5)

def clo(sock):
        # Close socket connection
        sock.close()
        print "Socket closed"

