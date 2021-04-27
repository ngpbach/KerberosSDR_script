#!/usr/bin/env python3
import time
import threading
import socket
import json
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)
import joystick as joy
import nucleo as target     # pixhawk or nucleo

radio_bearing = 0

def thread_get_bearing(UDP_IP = "127.0.0.1", UDP_PORT = 5005):
    global radio_bearing
    bearing_sock = socket.socket(socket.AF_INET, # Internet
                                socket.SOCK_DGRAM) # UDP
    bearing_sock.bind((UDP_IP, UDP_PORT))
    bearing_sock.settimeout(5)

    while True:
        try:
            message, addr = bearing_sock.recvfrom(1024) # buffer size is 1024 bytes
        except socket.timeout:
            log.warning("UDP: timed out waiting for bearing msg")
            continue

        try:
            data = json.loads(message.decode())
            radio_bearing = data["bearing"] - 45
        except json.JSONDecodeError:
            log.error("Msg: corrupt or incorrect format\nReceived msg: %s", message.decode())
            continue
        except KeyError:
            log.error("Msg: no [bearing] key received\nReceived msg: %s %s", message.decode())
            continue


def calculate_effort():
    yaw = 2*radio_bearing       # turning effort proportional to bearing
    return 0, yaw

if __name__ == "__main__":
    beartask = threading.Thread(target=thread_get_bearing)
    beartask.start()

    while(1):
        joy.joystick_update()
        js_active = joy.axes[5] > 0     # hold down RT button to use joystick
        if js_active:
            arm = joy.btns[0]       # press A to arm
            disarm = joy.btns[1]    # press B to disarm
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
            
            log.debug("Using radio homing control\n Pitch effort:{}\t Yaw effort: {}\t Armed: {}\t Link Hearbeat: {} Current bearing: {}".format(pitch, yaw, target.armed, target.heartbeat, radio_bearing))

        target.get_feedback()
        time.sleep(0.1)