#!/usr/bin/env python3
from os import POSIX_FADV_SEQUENTIAL
import time
import threading
import socket
import json
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.INFO)
import nucleo as target     # pixhawk or nucleo

PORT_RELAY = 5000
PORT_KERB = 5001
PORT_JS = 5002
LOCALHOST = "127.0.0.1"

class Joystick:
    """ Convenient class for getting joystick data from UDP packet """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_JS):
        self.axes = [0]*6
        self.btns = [0]*6
        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(10)
    
    def update(self):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            #log.debug(message)
            packet = json.loads(message.decode())
            self.axes = packet["ax"]
            self.btns = packet["bt"]
            
        except socket.timeout:
            log.debug("Socket timed out waiting for Joystick msg")
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())
        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)

class RadioCompass:
    """ Convenient class for getting radio compass data from UDP packet """
    def __init__(self, UDP_IP = "127.0.0.1", UDP_PORT = PORT_KERB):
        self.bearing = 0
        self.strength = 0
        self.confidence = 0
        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(10)
    
    def update(self):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            #log.debug(message)
            packet = json.loads(message.decode())
            self.bearing = packet["bearing"]
            self.strength = packet["strength"]
            self.confidence = packet["confidence"]
            
        except socket.timeout:
            log.debug("Socket timed out waiting for Radio Compass msg")
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())
        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)


class Telemetry:
    """ Convenient class for sending telemetry data to ground station through relay server """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_RELAY):
        self.sock = socket.socket(socket.AF_INET,   # Internet
                                socket.SOCK_DGRAM)  # UDP
    
    def update(self):
        packet = {}
        packet["type"] = "telem"
        packet["bearing"] = compass.bearing
        packet["arm"] = target.armed
        message = json.dumps(packet)
        # log.debug(message)            
        self.sock.sendto(message.encode(), (LOCALHOST, PORT_RELAY))


joy = Joystick()
compass = RadioCompass()
telem = Telemetry()

def calculate_effort():
    yaw = 0       # turning effort proportional to bearing
    return 0, yaw

def joystick_thread():
    while True:
        joy.update()

def compass_thread():
    while True:
        compass.update()

def telem_thread():
    while True:
        telem.update()
        time.sleep(1)

if __name__ == "__main__":
    joystick_task = threading.Thread(target=joystick_thread)
    compass_task = threading.Thread(target=compass_thread)
    telem_task = threading.Thread(target=telem_thread)
    joystick_task.start()
    compass_task.start()
    telem_task.start()

    while(1):
        js_active = joy.axes[2] > 0         # hold down LT button to use joystick
        if js_active:
            arm = joy.btns[0]               # press A to arm
            disarm = joy.btns[1]            # press B to disarm
            yaw = int(-joy.axes[0]*1000)    # left stick left-right for yaw
            pitch = int(-joy.axes[1]*1000)  # left stick up-down for pich

            if arm:
                if (pitch == 0 and yaw == 0):          
                    target.arm()
                else:
                    log.info("Joystick Pitch and Yaw must be neutral for arming")  

            if disarm:
                target.disarm()

            if target.armed:
                target.send_cmd(pitch, yaw)

            log.debug("Using joystick control\n Pitch effort: {}\t Yaw effort: {}\t Armed: {}\t Link Hearbeat: {}".format(pitch, yaw, target.armed, target.heartbeat))

        else:
            pitch, yaw = calculate_effort()
            if (target.armed):
                target.send_cmd(pitch, yaw)
            
            log.debug("Using radio homing control\n Pitch effort:{}\t Yaw effort: {}\t Armed: {}\t Link Hearbeat: {} Current bearing: {}".format(pitch, yaw, target.armed, target.heartbeat, compass.bearing))

        target.get_feedback()
        time.sleep(0.1)
