#!/usr/bin/env python3

import time
import atexit
import threading
import serial
import numpy as np
import json
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.DEBUG)
try:
    import joystick as joy
except Exception as msg:
    log.warning(msg)

""" Device specific settings """
BAUD = 9600    # baud of LORA UART
DEVICE = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0"       # requires platformio UDEV
# DEVICE = "./pttyin"

try:
    ser = serial.Serial(DEVICE, BAUD, timeout=5)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
    ser.reset_input_buffer()
except serial.SerialException as msg:
    log.error(msg)
    raise    

def terminate():
    send_command("exit")
    ser.close()

atexit.register(terminate)
     
WHOAMI = "gcs"
TARGET = "pi"

def send_command(cmd):
    try:
        packet = {}
        # Reducing message size to to low serial bandwidth
        # packet["origin"] = WHOAMI
        # packet["target"] = TARGET
        packet["type"] = "cmd"
        packet["act"] = cmd
        message = json.dumps(packet) + '\n'
        # log.debug("Sending: %s", message)
        ser.write(message.encode())
    except TypeError as msg:
        log.error(msg)

def send_joystick(axes, btns):
    try:
        packet = {}
        # Reducing message size to to low serial bandwidth
        # packet["origin"] = WHOAMI
        # packet["target"] = TARGET
        packet["type"] = "js"
        packet["ax"] = [round(num, 3) for num in axes[0:3]]      # only need 3 axes, with 3 decimal places
        packet["bt"] = btns[0:2]      # only need 2 buttons
        message = json.dumps(packet) + '\n'
        # log.debug("Sending: %s", message)
        ser.write(message.encode())
    except TypeError as msg:
        log.error(msg)

def get_feedback():
    try:
        message = ser.readline()
        if not message:
            log.error("Serial read timeout")

        log.debug(message)                
        # packet = json.loads(message.decode())
        
    except json.JSONDecodeError:
        log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)
    except KeyError as msg:
        log.error("Packet received has no [%s] key", msg)

def get_feedback_thread():
    while True:
        get_feedback()

def send_joystick_thread():
    while True:
        joy.joystick_update()
        if (joy.btns[7]):
            send_command("exit")
            exit()

        send_joystick(joy.axes, joy.btns)
        time.sleep(1)     # wireless serial is slow

if __name__ == "__main__":
    getfeedback_task = threading.Thread(target=get_feedback_thread, daemon=True)
    send_joystick_task = threading.Thread(target=send_joystick_thread)
    getfeedback_task.start()
    send_joystick_task.start()
    log.info("\n\tHold LT and press A to arm.\n\tHold LT and use left joystick to control.\n\tHold LT and press B to disarm.\n\tPress Start to exit (switch Companion Pi Lora Serial to Shell mode) ")
