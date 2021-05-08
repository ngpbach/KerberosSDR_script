#!/usr/bin/env python3

import time
import random
import signal
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
    raise

""" LORA serial settings """
DEVICE = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0"       # requires platformio UDEV
BAUD = 9600    # baud of LORA UART
# DEVICE = "./pttyin"

try:
    ser = serial.Serial(DEVICE, BAUD, timeout=0.5)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
    ser.reset_input_buffer()
except serial.SerialException as msg:
    log.error(msg)
    raise    

def terminate():
    ser.close()

atexit.register(terminate)

def handler(signal_received, frame):
    terminate()

# Tell Python to run the handler() function when SIGINT is recieved
signal.signal(signal.SIGINT, handler) # ctlr + c
signal.signal(signal.SIGTSTP, handler) # ctlr + z
     
WHOAMI = "gcs"
TARGET = "pi"

def send_command(cmd):
    try:
        packet = {}
        # Reducing message size to to low serial bandwidth
        # packet["origin"] = WHOAMI
        # packet["target"] = TARGET
        packet["type"] = "cmd"
        packet["cmd"] = cmd
        message = json.dumps(packet) + '\n'
        # log.debug("Sending: %s", message)
        read_mutex.acquire()
        ser.write(message.encode())
        packet = get_feedback("ack")
        read_mutex.release()

        if packet and packet["cmd"] == cmd:
            return True
        else:
            return False

    except TypeError as msg:
        log.error(msg)

def send_joystick(axes, btns):
    try:
        packet = {}
        # Reducing message size low serial bandwidth
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

read_mutex = threading.Lock()
buffer = ''
def get_feedback(type="telem"):
    global buffer
    try:
        message = ser.readline().decode()
        if not message or message[-1] != '\n':
            buffer += message
            return
        else:
            message = buffer + message
            buffer = ''

        # log.debug(message)
        packet = json.loads(message)
        if packet["type"] == type:
            return packet
    

    except UnicodeDecodeError:
        log.error("Gargabe characters received: %s", message)
    except json.JSONDecodeError:
        time.sleep(0.33)
        log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)
    except KeyError as msg:
        log.error("Packet received has no [%s] key", msg)

def get_feedback_thread():
    while True:
        read_mutex.acquire()
        get_feedback()
        read_mutex.release()


def send_joystick_thread():
    while True:
        joy.joystick_update()
        if (joy.btns[7]):
            ack = send_command("exit")
            if ack:
                log.info("Pi relay server exited successfully")
            else:
                log.warning("Pi relay server might have failed to exit")

            exit(0)


        send_joystick(joy.axes, joy.btns)
        # Sleep an odd fraction of second. This is a work around for the weird bug where sometime the script start at just the wrong
        # moment, and consistently receiving incomplete packet with exactly the same length.
        # A theory that need to be investigated, is that the transmitting from local Lora module
        # and receiving from remote Lora module coincidentally synced up and causing colision 
        # in the Lora module, either in the shared rx/tx buffer, or in the packet processing stage.
        # (it's not due to the serial read & write timing in the local code, but rather the transmission timing of the local and remote Lora module)
        # Either way, if such event occur the incoming packet will be consistently incomplete.
        # One way to correct that is to "desync" by having odd period for one Lora module and even period for the other Lora module
        time.sleep(1)

if __name__ == "__main__":
    # getfeedback_task = threading.Thread(target=get_feedback_thread, daemon=True)
    # send_joystick_task = threading.Thread(target=send_joystick_thread)
    # getfeedback_task.start()
    # send_joystick_task.start()
    log.info("\n\tHold LT and press A to arm.\n\tHold LT and use left joystick to control.\n\tHold LT and press B to disarm.\n\tPress Start switch Companion Pi Lora Serial to Shell mode")
    
    while True:
        joy.joystick_update()
        if (joy.btns[7]):
            ack = send_command("exit")
            if ack:
                log.info("Pi relay server exited successfully")
            else:
                log.warning("Pi relay server might have failed to exit")

            exit(0)

        send_joystick(joy.axes, joy.btns)
        time.sleep(1)
        get_feedback()