#!/usr/bin/env python3

import time
import threading
import serial
import numpy as np
import json
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)
try:
    import joystick as joy
except Exception as msg:
    log.warning(msg)

""" Device specific settings """
BAUD = 9600    # baud of LORA UART
DEVICE = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0"       # requires platformio UDEV
# DEVICE = "./pttyin"

LOCALHOST = "127.0.0.1"
PORT = 5000

try:
    ser = serial.Serial(DEVICE, BAUD, timeout=0.1)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
    ser.reset_input_buffer()
except serial.SerialException as msg:
    log.error(msg)
    raise    

def terminate():
    ser.close()
     
WHOAMI = "gcs"
TARGET = "pi"

def send_joystick(axes, btns):
    try:
        packet = {}
        # Reducing message size to to low serial bandwidth
        # packet["origin"] = WHOAMI
        # packet["target"] = TARGET
        packet["type"] = "js"
        packet["ax"] = [round(num, 3) for num in axes[0:4]]      # only need 4 axes, with 3 decimal places
        packet["bt"] = btns[0:2]      # only need 2 buttons
        message = json.dumps(packet) + '\n'
        # log.debug("Sending:", message)
        ser.write(message.encode())
    except TypeError as msg:
        log.error(msg)

def get_feedback():
    while True:
        try:
            ser.timeout = 10
            message = ser.readline()
            log.debug(message)                
            # packet = json.loads(message.decode())
            
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)
        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)

if __name__ == "__main__":
    getfeedback_task = threading.Thread(target=get_feedback)
    getfeedback_task.start()
    while(1):
        joy.joystick_update()
        send_joystick(joy.axes,joy.btns)
        # log.debug("\n\tAxes value: {}\n\tButtons value: {}\n\tArrows value: {}".format(joy.axes, joy.btns, joy.arrws))
        time.sleep(0.2)
