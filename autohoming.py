#!/usr/bin/env python3
from os import POSIX_FADV_SEQUENTIAL
import time
import threading
import socket
import json
from gpiozero import PWMLED
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
PORT_CMD = 5003
PORT_VISION = 5004
LOCALHOST = "127.0.0.1"
VISION_IP = ''

""" PID settings """
SETPOINT_TOLERANCE = 20             # angle in degrees, within which the ship heading can be considered "good enough" for proceeding toward the beacon
SETPOINT_REACHED_WAIT_PERIOD = 3    # time in seconds before yaw angle is considered stable and ship is ready to move toward the beacon
FORWARD_SPEED = 200                 # speed (max 1000) the ship move forward
YAW_SPEED = 100                     # speed the ship yaw to turn toward the goal

""" Helper classes """
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
                self.axes = packet.get("ax",[0]*6)
                self.btns = packet.get("bt",[0]*6)
            else:
                self.reset()
            
        except socket.timeout:
            self.reset()
            log.debug("Socket timed out waiting for Joystick msg")
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())
        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)

class Vision:
    def __init__(self, UDP_IP = VISION_IP, UDP_PORT = PORT_VISION):
        self.bearing = None
        self.distance = None

        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(1)

        self.reset()

    def reset(self):
        self.bearing = None
        self.distance = None

    def update(self):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            # log.debug(message)
            packet = json.loads(message.decode())

            if packet.get("type") == "vision":
                self.bearing = packet.get("bearing") or None
                self.distance = packet.get("distance") or None

        except socket.timeout:
            self.reset()
            log.debug("Socket timed out waiting for Vision msg")
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())

class RadioCompass:
    """ Convenient class for getting radio compass data from UDP packet """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_KERB):
        self.bearing = None
        self.raw_bearing = None
        self.power = 0
        self.confidence = 0
        self.confident = False
        self.min_power = 5           # minimum strength to be considered valid
        self.min_confidence = 5      # minimum confidence to be considered valid
        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(10)
    
    def reset(self):
        self.bearing = None
        self.power = 0
        self.confidence = 0
        self.confident = False

    def update(self):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            log.info(message)
            packet = json.loads(message.decode())
            self.power = packet.get("power") or 0
            self.confidence = packet.get("confidence") or 0
            log.debug("Min Power {}, Min Confidence {}".format(self.min_power, self.min_confidence))
            self.confident = self.power >= self.min_power and self.confidence >= self.min_confidence
            self.bearing = packet.get("bearing") - 45 or None
            if self.bearing and self.bearing > 180:
                self.bearing = -(360 - self.bearing)

            
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
    
    def update(self, pixhawk, compass, pid, effort):
        packet = {}
        packet["type"] = "telem"
        packet["heartbeat"] = pixhawk.heartbeat
        packet["bearing"] = compass.bearing
        packet["confident"] = compass.confident
        packet["arm"] = pixhawk.armed
        packet["pidparams"] = [pid.Kp, pid.Ki, pid.Kd]
        packet["effort(p,y)"] = [effort.pitch, effort.yaw]
        message = json.dumps(packet)
        # log.debug(message)            
        self.sock.sendto(message.encode(), (LOCALHOST, PORT_RELAY))


class CMDProcessor:
    """ Convenient class for tuning PID through UDP """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_CMD):
        self.sock = socket.socket(socket.AF_INET, # Internet
                                    socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(None)

        self.arming = False
        self.disarming = False
        
    def update(self, pid):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
            log.info(message)
            packet = json.loads(message.decode())

            if packet.get("type") == "cmd":
                if packet.get("cmd") == "tune":
                    pid.Kp = packet.get('Kp')
                    pid.Ki = packet.get('Ki')
                    pid.Kd = packet.get('Kd')

                elif packet.get("cmd") == "arm":
                    if packet.get("arm"):
                        self.arming = True
                    else:
                        self.disarming = True

                elif packet.get("cmd") == "threshold":
                    compass.min_confidence = packet.get('conf')
                    compass.min_power = packet.get('power')

        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\nReceived msg: %s", message.decode())

class Effort:
    """ Struct for storing current pitch and yaw effort """
    def __init__(self):
        self.pitch = 0
        self.yaw = 0
        self.deadzone_low = -100
        self.deadzone_high = 100

"""" Initialize helper objects """
pixhawk = Pixhawk(DEVICE, BAUD)
joy = Joystick()
compass = RadioCompass()
vision = Vision()
telem = Telemetry()
cmdproc = CMDProcessor()
effort = Effort()
yaw_pid = PID(Kp=0.3, Ki=0.01, Kd=0.6, setpoint=0, sample_time=0.5, output_limits=(-0.2,0.2))

""" Worker tasks """
def joystick_thread():
    while True:
        joy.update()

def compass_thread():
    while True:
        compass.update()

def vision_thread():
    while True:
        vision.update()

def relay_thread():
    while True:
        telem.update(pixhawk, compass, yaw_pid, effort)
        time.sleep(1)

def get_feedback_thread():
    while True:
        pixhawk.get_feedback()
        time.sleep(1)

def cmdproc_thread():
    while True:
        cmdproc.update(yaw_pid)

class StatusLED():
    def __init__(self):
        self.led = PWMLED(18)
        self._mode = -1

    def pulse_slow(self):
        if self._mode != 0:
            self._mode = 0
            self.led.pulse(fade_in_time=1, fade_out_time=1)

    def blink_slow(self):
        if self._mode != 1:
            self._mode = 1
            self.led.blink(on_time=0.5, off_time=0.5)

    def blink_fast(self):
        if self._mode != 2:
            self._mode = 2
            self.led.blink(on_time=0.1, off_time=0.1)

    def flash(self):
        if self._mode != 3:
            self._mode = 3
            self.led.blink(on_time=0.01, off_time=1)
    
    def flash_inverse(self):
        if self._mode != 4:
            self._mode = 4
            self.led.blink(on_time=1, off_time=0.01)

""" Main loop """
def main():
    led = StatusLED()
    setpoint_timer = Timer(SETPOINT_REACHED_WAIT_PERIOD)

    while(1):
        time.sleep(0.1)

        if not pixhawk.armed and cmdproc.arming:
            pixhawk.arm()
            cmdproc.arming = False

        elif pixhawk.armed and cmdproc.disarming:
            effort.yaw = 0
            effort.pitch = 0
            yaw_pid.reset()
            pixhawk.send_cmd(effort.pitch, effort.yaw)
            pixhawk.disarm()
            cmdproc.disarming = False

        if pixhawk.armed:
            js_active = joy.axes[2] > 0         # hold down LT button to use joystick
            if js_active:
                effort.yaw = int(joy.axes[0]*1000)    # left stick left-right for turn left-right
                effort.pitch = int(joy.axes[1]*1000)  # left stick up-down for forward-backward

                led.blink_fast()
                log.info("Using joystick control")
            
            elif compass.bearing and compass.confident:
                # effort.yaw = -int(yaw_pid(compass.bearing/180) * 1000)      # Calculate PID based on scaled feedback
                # if effort.yaw < -50 and effort.yaw > effort.deadzone_low:
                #     effort.yaw = effort.deadzone_low
                # elif effort.yaw > 50 and effort.yaw < effort.deadzone_high:
                #     effort.yaw = effort.deadzone_high

                if compass.bearing > -SETPOINT_TOLERANCE and compass.bearing < SETPOINT_TOLERANCE:
                    effort.yaw = -int(yaw_pid(compass.bearing/180) * 1000)      # Calculate PID based on scaled feedback

                    if setpoint_timer():              
                        effort.pitch = -FORWARD_SPEED
                        led.blink_fast()

                    if vision.distance and vision.distance < 100:
                        Kp_pitch = 2
                        effort.pitch = -vision.distance*Kp_pitch
                                      
                else:
                    if compass.bearing < 0:
                        effort.yaw = YAW_SPEED
                    elif compass.bearing > 0:
                        effort.yaw = -YAW_SPEED

                    led.flash()
                    setpoint_timer.reset()
                    yaw_pid.reset()
                    effort.pitch = 0
                
                log.info("Using radio homing control")
                log.info("PID params: {} {} {}".format(yaw_pid.Kp, yaw_pid.Ki, yaw_pid.Kd))

            else:
                effort.yaw = 0
                effort.pitch = 0
                yaw_pid.reset()

                led.blink_slow()
                log.info("Waiting for compass bearing")

            pixhawk.send_cmd(effort.pitch, effort.yaw)      # negative pitch is going forward, negative yaw is left turn    
            log.info("Effort pitch: {}, Effort yaw: {}".format(effort.pitch, effort.yaw))
        
        else:
            led.pulse_slow()
            log.info("Idling")
        
        log.info("Pitch effort:{}\tYaw effort: {}\tArmed: {}\tLink Hearbeat: {}".format(effort.pitch, effort.yaw, pixhawk.armed, pixhawk.heartbeat))
        log.info("Current radio bearing: {}\tPower: {}\tConfidence: {}\tCurrent vision bearing: {}\tCurrent vision distance: {}".format(compass.bearing, compass.power, compass.confidence, vision.bearing, vision.distance))









if __name__ == "__main__":
    joystick_task = threading.Thread(target=joystick_thread)
    compass_task = threading.Thread(target=compass_thread)
    vision_task = threading.Thread(target=vision_thread)
    relay_task = threading.Thread(target=relay_thread)
    get_feedback_task = threading.Thread(target=get_feedback_thread)
    cmdproc_task = threading.Thread(target=cmdproc_thread)
    joystick_task.start()
    compass_task.start()
    vision_task.start()
    relay_task.start()
    get_feedback_task.start()
    cmdproc_task.start()

    main()

