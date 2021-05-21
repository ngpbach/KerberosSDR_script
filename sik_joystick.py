#!/usr/bin/env python3

import time
import threading
try:
    import joystick as joy
except Exception as msg:
    raise
from pixhawk import Pixhawk     # pixhawk or nucleo
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

""" Sik Radio settings """
DEVICE = "/dev/serial/by-id/usb-Silicon_Labs_CP2104_USB_to_UART_Bridge_Controller_01E97D63-if00-port0"
BAUD = 57200

def telem_thread():
    while True:
        pixhawk.get_feedback()
        time.sleep(1)

if __name__ == "__main__":
    pixhawk = Pixhawk(DEVICE, BAUD)
    telem_task = threading.Thread(target=telem_thread)
    telem_task.start()

    while(1):
        joy.joystick_update()
        js_active = joy.axes[2] > 0     # hold down LT button to use joystick
        if js_active:
            arming = joy.btns[0]               # press A to arm
            disarming = joy.btns[1]            # press B to disarm
            yaw = int(joy.axes[0]*1000)    # left stick left-right for yaw
            pitch = int(joy.axes[1]*1000)  # left stick up-down for pich

            if arming and not pixhawk.armed:
                if (pitch == 0 and yaw == 0):          
                    pixhawk.arm()
                else:
                    log.info("Joystick Pitch and Yaw must be neutral for arming")  

            if disarming and pixhawk.armed:
                pixhawk.disarm()

            if pixhawk.armed:
                pixhawk.send_cmd(pitch, yaw)

        time.sleep(0.1)