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
        target.get_feedback()
        time.sleep(0.1)

if __name__ == "__main__":
    target = Pixhawk(DEVICE, BAUD)
    telem_task = threading.Thread(target=telem_thread)
    telem_task.start()

    while(1):
        joy.joystick_update()
        js_active = joy.axes[2] > 0     # hold down LT button to use joystick
        if js_active:
            log.debug("Armed:%s", target.armed)
            arm = joy.btns[0]
            disarm = joy.btns[1]
            yaw = int(-joy.axes[0]*1000)    # left stick left-right for yaw
            pitch = int(-joy.axes[1]*1000)  # left stick up-down for pitch

            if (target.armed):
                target.send_cmd(pitch, yaw)
                log.debug("sending {} {}".format(pitch,yaw))

            if arm:      # press A to arm    
                if (pitch == 0 and yaw == 0):
                    target.arm()
                else:
                    log.info("Joystick Pitch and Yaw must be neutral for arming")

            if disarm:   # press B to disarm
                target.disarm()

        time.sleep(0.1)