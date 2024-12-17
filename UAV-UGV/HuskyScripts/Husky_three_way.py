#!/usr/bin/python
import rospy
from gps_common.msg import GPSFix
from sensor_msgs.msg import NavSatFix
from Send_mission_lib import send_mission
import fcntl, os
import errno
import socket
import pickle
import time
import sys
import threading
import Arm
import queue

HEADERSIZE = 8
LOG_INTERVAL = 1
THRESHOLD = 0.0001
loc = {'lat': None, 'lon': None}
target_loc = {'lat': -91, 'lon': -181}
previous_target = None
target_queue = queue.Queue()

def recive_data(sock):
    buffer = b''
    try:
        buffer = sock.recv(HEADERSIZE)
    except socket.error as e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            # print("nothing recived")
            return b''
        else:
            print(e)
            sys.exit(1)
    if len(buffer) != 0:
        print("alleget packet length: {}".format(buffer.decode("utf-8")))
        full_msg = b''
        while len(full_msg) < int(buffer):
            full_msg = full_msg + sock.recv(int(buffer) - len(full_msg))
        decode = pickle.loads(full_msg)
        return decode


def send_data(data, sock, h_size):
    packet = pickle.dumps(data)
    packet = '{:<{}}'.format(len(packet), h_size).encode('utf-8') + packet
    sock.send(packet)


def update_location():
    global loc
    loc = {'lat': data.latitude, 'lon': data.longitude}

def run_send_mission():
    global target_loc
    send_mission(target_loc)
"""
    Connects to the ground station and the drone. Receives data from the drone and sends data to the Send Mission Script.
"""
# GROUND_STATION = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# GROUND_STATION.connect(('192.168.1.4', 11234))
# fcntl.fcntl(GROUND_STATION, fcntl.F_SETFL, os.O_NONBLOCK)

#GROUND_STATION = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#GROUND_STATION.connect(('192.168.137.54', 11237))
#fcntl.fcntl(GROUND_STATION, fcntl.F_SETFL, os.O_NONBLOCK)

#send_data('HUSKY', GROUND_STATION, HEADERSIZE)

def main():
    global previous_target, target_loc

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 11234))
    s.listen(5)

    clientsocket, address = s.accept()
    fcntl.fcntl(clientsocket, fcntl.F_SETFL, os.O_NONBLOCK)

    id = b''
    while len(id) == 0: # Change this once the ground station is working
        id = recive_data(clientsocket)
    print("Drone connected")

    DRONE = {'socket': None, 'addr': None}

    if id == 'DRONE':
        DRONE['socket'] = clientsocket
        DRONE['addr'] = address


    # subscribe to GPS topic and post it to loc dictionary
    # in the call back function do not forget
    last_log = time.time()

    rospy.init_node("comunication_node")

    #pub = rospy.Publisher("/drone_goal", GPSFix, queue_size=10)
    #rospy.Subscriber("/piksi_position/navsatfix_spp", NavSatFix, update_location)
    #print("publisher initialized")

    while True:
        active_threads = [thread.name for thread in threading.enumerate()]    
        # Sends the location of the Husky to the ground station
        if time.time() - last_log >= LOG_INTERVAL:
            last_log = time.time()
    #       send_data(loc, GROUND_STATION, HEADERSIZE)
    #        print("Sending data to ground station")
        target = recive_data(DRONE['socket'])
#        print(target)
        # Make sure the target is a dictionary
        if isinstance(target, dict):
            target = {str(k) : v for k,v in target.items()}

            print("INFO: Received target location: " + str(target))
            # To prevent overloading the Husky's mission planner, only send the target location if it is different from the previous target location
            if previous_target is None or (abs(target['lat'] - previous_target['lat']) > THRESHOLD or abs(target['lon'] - previous_target['lon']) > THRESHOLD):
                    previous_target = target
                    target_loc = target
                    target_queue.put(target_loc)
                    # To prevent overloading send missions, make sure only one mission thread is running at a time and iterate through the queue of target locations
        if not any("send_mission" in thread for thread in active_threads) and not target_queue.empty():
            # Track how many send mission threads have been made
            mission_n += 1
            print("starting new mission #"+str(mission_n))
            current_mission = threading.Thread(target=send_mission,daemon=True,args=(target_queue.get()),name="send_mission-"+str(mission_n))
            current_mission.start()
        time.sleep(0.4)


if __name__ == "__main__":
     main()
#     Arm.publisher(['a', 'i', 'i', 'i', 'i'], 3)
#     sock = Arm.soc1()
#     Arm.Arm1(sock)
#    Arm.publisher(['a', 'p', '255'], 3)
#     Arm.Arm2(sock)
#     Arm.publisher(['a', 'c', 'r'], 3)
#     Arm.clo(sock)
