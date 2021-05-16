#!/usr/bin/env python3
from os import POSIX_FADV_SEQUENTIAL
import time
import threading
import socket
import json
from simple_pid import PID
from pixhawk import Pixhawk     # pixhawk or nucleo
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.DEBUG)


""" Pixhawk USB connection settings """
DEVICE = "/dev/serial/by-id/usb-ArduPilot_Pixhawk1_360027001051303239353934-if00"
BAUD = 115200

""" UDP ports settings"""
PORT_RELAY = 5000
PORT_KERB = 5001
PORT_JS = 5002
PORT_PID = 5003
LOCALHOST = "127.0.0.1"


""" Radio compass settings """
STRENGTH_MIN = 10        # minimum strength to be considered valid
CONFIDENCE_MIN = 5      # minimum confidence to be considered valid

""" PID settings """
SETPOINT_TOLERANCE = 10             # angle in degrees, within which the ship heading can be considered "good enough" for proceeding toward the beacon
SETPOINT_REACHED_WAIT_PERIOD = 3    # time in seconds before yaw angle is considered stable and ship is ready to move toward the beacon
FORWARD_SPEED = 200                 # speed (max 1000) the ship move forward

class Timer:
    """ Convenient class for executing non timing-critical action periodically """
    def __init__(self, duration):
        self.duration = duration
        self.start_time = time.time()

    def __call__(self):
        if time.time() - self.start_time > self.duration:
            self.reset()
            return True
        else:
            return False

    def reset(self):
        self.start_time = time.time()

class Joystick:
    """ Convenient class for getting joystick data from UDP packet """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_JS):
        self.axes = [0]*6
        self.btns = [0]*6
        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(1)

    def reset(self):
        self.axes = [0]*6
        self.btns = [0]*6
    
    def update(self):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            #log.debug(message)
            packet = json.loads(message.decode())
            if packet.get("type") == "js":
                self.axes = packet.get("ax", [0]*6)
                self.btns = packet.get("bt"[0]*6)
            else:
                self.reset()
            
        except socket.timeout:
            self.reset()
            log.debug("Socket timed out waiting for Joystick msg")
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())
        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)

class RadioCompass:
    """ Convenient class for getting radio compass data from UDP packet """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_KERB):
        self.bearing = None
        self.power = 0
        self.confidence = 0
        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(10)
    
    def reset(self):
        self.bearing = None
        self.power = 0
        self.confidence = 0

    def update(self):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            # log.info(message)
            packet = json.loads(message.decode())
            self.strength = packet.get("strength", 0)
            self.confidence = packet.get("confidence", 0)

            if self.strength > STRENGTH_MIN and self.confidence > CONFIDENCE_MIN:
                self.bearing = packet.get("bearing", None)
                if self.bearing > 180:
                    self.bearing = -(360 - self.bearing)

            else:
                self.bearing = None
            
        except socket.timeout:
            self.reset()
            log.debug("Socket timed out waiting for Radio Compass msg")
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())


class Telemetry:
    """ Convenient class for sending telemetry data to ground station through UDP"""
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_RELAY):
        self.sock = socket.socket(socket.AF_INET,   # Internet
                                socket.SOCK_DGRAM)  # UDP
    
    def update(self, pixhawk, compass):
        packet = {}
        packet["type"] = "telem"
        packet["bearing"] = compass.bearing
        packet["arm"] = pixhawk.armed
        packet["heartbeat"] = pixhawk.heartbeat
        message = json.dumps(packet)
        # log.debug(message)            
        self.sock.sendto(message.encode(), (LOCALHOST, PORT_RELAY))


class PIDtune:
    """ Convenient class for tuning PID through UDP """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_PID):
        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(None)
        
    def update(self, pid):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            # log.info(message)
            packet = json.loads(message.decode())

            if packet.get("type") == "tune":
                pid.Kp = packet.get('Kp', 0)
                pid.Ki = packet.get('Ki', 0)
                pid.Kd = packet.get('Kd', 0)

        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())


pixhawk = Pixhawk(DEVICE, BAUD)
joy = Joystick()
compass = RadioCompass()
telem = Telemetry()
tune = PIDtune()
yaw_pid = PID(Kp=0.3, Ki=0, Kd=1, setpoint=0, sample_time=0.5, output_limits=(-1,1))

def joystick_thread():
    while True:
        joy.update()

def compass_thread():
    while True:
        compass.update()

def relay_thread():
    while True:
        telem.update(pixhawk, compass)
        time.sleep(1)

def telem_thread():
    while True:
        target.get_feedback()
        time.sleep(1)

def pidtune_thread():
    while True:
        tune.update(yaw_pid)

if __name__ == "__main__":
    joystick_task = threading.Thread(target=joystick_thread)
    compass_task = threading.Thread(target=compass_thread)
    relay_task = threading.Thread(target=relay_thread)
    telem_task = threading.Thread(target=telem_thread)
    pidtune_task = threading.Thread(target=pidtune_thread)
    joystick_task.start()
    compass_task.start()
    relay_task.start()
    telem_task.start()
    pidtune_task.start()

    setpoint_timer = Timer(SETPOINT_REACHED_WAIT_PERIOD)
    while(1):
        js_active = joy.axes[2] > 0         # hold down LT button to use joystick
        if js_active:
            arming = joy.btns[0]               # press A to arm
            disarming = joy.btns[1]            # press B to disarm
            yaw = int(-joy.axes[0]*1000)    # left stick left-right for yaw
            pitch = int(-joy.axes[1]*1000)  # left stick up-down for pich

            if arming and not pixhawk.armed:
                if (pitch == 0 and yaw == 0):          
                    pixhawk.arm()
                else:
                    log.info("Joystick Pitch and Yaw must be neutral for arming")  

            if disarming and pixhawk.armed:
                pixhawk.disarm()

            if pixhawk.armed:
                pixhawk.send_cmd(pitch, yaw)

            log.info("Using joystick control\n Pitch effort: {}\t Yaw effort: {}\t Armed: {}\t Link Hearbeat: {}".format(pitch, yaw, pixhawk.armed, pixhawk.heartbeat))

        elif pixhawk.armed:
            if compass.bearing:
                yaw = -yaw_pid(compass.bearing/180) * 1000      # Calculate PID based on scaled feedback

                if compass.bearing > -SETPOINT_TOLERANCE and compass.bearing < SETPOINT_TOLERANCE:
                    if setpoint_timer():                
                        pitch = -FORWARD_SPEED

                else:
                    setpoint_timer.reset()
                    pitch = 0

            else:
                yaw = 0
                pitch = 0
                yaw_pid.reset()

            pixhawk.send_cmd(pitch, yaw)
            
            log.info("Using radio homing control\n Pitch effort:{}\t Yaw effort: {}\t Armed: {}\t Link Hearbeat: {}\t Current bearing: {}".format(pitch, yaw, pixhawk.armed, pixhawk.heartbeat, compass.bearing))
            
        time.sleep(0.1)
