#!/usr/bin/env python3
import time
import threading
import socket
import json
import nucleo as target     # pixhawk or nucleo
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

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
    target.arm()

    while(1):
        log.info("Current bearing %s:", radio_bearing)
        pitch, yaw = calculate_effort()
        target.send_cmd(pitch, yaw)
        target.get_feedback()
        time.sleep(0.1)