#!/usr/bin/python
import time
from threading import Thread
from MavLink import MavLink
from Detector import Detector
import sys
import socket
import errno
import fcntl, os
import pickle


class Network:

    def __init__(self, GS_dict, HUSKY_dict, GPS_class: MavLink, detector: Detector, log_int, cool_down_min):
        self.HEADERSIZE = 8
        self.cooldown = float(cool_down_min) * 6
        self.LOG_INTERVAL = float(log_int)
        self.last_cords_send_timestamp = 0

        self.GPS = GPS_class
        self.detectNet = detector

        self.GS_dict = GS_dict
        self.HUSKY_dict = HUSKY_dict

        print("NETWORKING:    GS dict", (self.GS_dict[0], int(self.GS_dict[1])))
        print("NETWORKING:    HUSKY Dict", (self.HUSKY_dict[0], int(self.HUSKY_dict[1])))
#        self.GS = self.connect((self.GS_dict[0], int(self.GS_dict[1])))
        self.HUSKY = self.connect((self.HUSKY_dict[0], int(self.HUSKY_dict[1])))
        time.sleep(0.3)

#        self.send_to_GS("DRONE")
        self.send_to_HUSKY("DRONE")

        self.is_rinning = True
        self.thread = Thread(target=self.loop, args=())
        self.thread.deamon = True
        self.thread.start()

    def loop(self):
        last_log = 0.0
        persons_loc, detection_timestamp = self.detectNet.get_data()
        while self.is_rinning:
#           gs_received_data = self.receive_data(self.GS)
           gs_received_data = None 
           if gs_received_data == '1':
                print("NTWORKING:   Sending persons location (manual overwrite)")
                self.last_cords_send_timestamp = time.time()
                self.send_to_HUSKY(persons_loc)
           if time.time() - last_log >= self.LOG_INTERVAL:
                last_log = time.time()
                while not self.GPS.allow_read:
                    pass
#                self.send_to_GS(self.GPS.loc)
           if persons_loc is not None \
                    and self.last_cords_send_timestamp + self.cooldown < detection_timestamp:
                print("\n!!!\n!!!\nNTWORKING:   Sending location to the HUSKY\n!!!\n!!!")
                self.last_cords_send_timestamp = time.time()
                self.send_to_HUSKY(persons_loc)


    def connect(self, IP_Port_dict: dict):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.connect(IP_Port_dict)
        fcntl.fcntl(soc, fcntl.F_SETFL, os.O_NONBLOCK)
        # soc.setblocking(True)

        return soc

    def receive_data(self, sock):
        buffer = b''
        try:
            buffer = sock.recv(self.HEADERSIZE)
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

    def send_data(self, soc: socket, data, protocol):
        bit_data = pickle.dumps(data, protocol)
        message = '{:<{}}'.format(len(bit_data), self.HEADERSIZE).encode('utf-8') + bit_data
        soc.send(message)

    def send_to_GS(self, data):
        self.send_data(self.GS, data, 4)

    def send_to_HUSKY(self, data):
        self.send_data(self.HUSKY, data, 2)

    def is_thread_alive(self):
        return self.thread.is_alive()

    def kill(self):

        self.is_rinning = False
        self.thread.join()
        self.HUSKY.close()
 #       self.GS.close()
