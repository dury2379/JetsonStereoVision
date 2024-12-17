#!/usr/bin/python3

"""
This scripts pretends to be the Drone to test the communication between the Husky and the Drone.
It will send the location of the drone to the Husky.
"""

import time
from threading import Thread
import sys
import socket
import errno
import fcntl, os
import pickle


class Network:

    def __init__(self, HUSKY_dict, log_int, cool_down_min):
        self.HEADERSIZE = 8
        self.cooldown = float(cool_down_min) * 6
        self.LOG_INTERVAL = float(log_int)
        self.last_cords_send_timestamp = 0

        self.HUSKY_dict = HUSKY_dict

        self.HUSKY = self.connect((self.HUSKY_dict[0], int(self.HUSKY_dict[1])))
        time.sleep(0.3)

        self.send_to_HUSKY("DRONE")

        self.is_rinning = True
        self.thread = Thread(target=self.loop, args=())
        self.thread.deamon = True
        self.thread.start()

    def loop(self):
        # Set example data to send to the Husky/ generate the last 3 digits of the GPS coordinates
        lat = 34.059 + (random.random() * 0.0001 - 0.00005)
        lon = -117.821 + (random.random() * 0.0001 - 0.00005)
        print("NETWORKING: Sending location to the Husky: ", lat, lon)
        persons_loc, detection_timestamp = {'lat': lat, 'lon': lon}, time.time()
        while self.is_rinning:
            if persons_loc is not None \
                    and self.last_cords_send_timestamp + self.cooldown < detection_timestamp:
                print("\n!!!\n!!!\nNTWORKING:   Sending location to the HUSKY\n!!!\n!!!")
                self.last_cords_send_timestamp = time.time()
                self.send_to_HUSKY(persons_loc)

    def connect(self, IP_Port_dict: dict):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.connect(IP_Port_dict)
        fcntl.fcntl(soc, fcntl.F_SETFL, os.O_NONBLOCK)

        return soc

    def send_data(self, soc: socket, data, protocol):
        bit_data = pickle.dumps(data, protocol)
        message = '{:<{}}'.format(len(bit_data), self.HEADERSIZE).encode('utf-8') + bit_data
        soc.send(message)

    def send_to_HUSKY(self, data):
        self.send_data(self.HUSKY, data, 2)

    def is_thread_alive(self):
        return self.thread.is_alive()

    def kill(self):
        self.is_rinning = False
        self.thread.join()
        self.HUSKY.close()

def main():
    net = Network(('192.168.131.1', 11234), 5, 3)
    time.sleep(10)
    net.kill()
    
if __name__ == "__main__":
    main()
