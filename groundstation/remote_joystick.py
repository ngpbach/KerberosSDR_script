#!/usr/bin/env python3

import time
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
try:
    ser = serial.Serial(DEVICE, BAUD)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
    ser.reset_input_buffer()
except serial.SerialException as msg:
    log.error(msg)
    raise

def terminate():
    ser.close()
     
WHOAMI = "gcs"
TARGET = "pi"

def _make_json_packet(axes, btns):
    packet = {}
    # Reducing message size to to low serial bandwidth
    # packet["origin"] = WHOAMI
    # packet["target"] = TARGET
    packet["type"] = "js"
    packet["ax"] = [round(num, 3) for num in axes[0:4]]      # only need 4 axes, with 3 decimal places
    packet["bt"] = btns[0:2]      # only need 2 buttons
    try:
        text = json.dumps(packet) + '\n'
        return text.encode()
        # log.debug("Sending:", text)
    except TypeError as msg:
        log.error(msg)

if __name__ == "__main__":
    while(1):
        joy.joystick_update()
        packet = _make_json_packet(joy.axes,joy.btns)
        ser.write(packet)
        log.debug("\n\tAxes value: {}\n\tButtons value: {}\n\tArrows value: {}".format(joy.axes, joy.btns, joy.arrws))
        time.sleep(0.2)
