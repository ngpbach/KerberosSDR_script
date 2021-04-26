#!/usr/bin/env python3

import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)
import time
try:
    import joystick as joy
except UserWarning as msg:
    log.warning(msg)

import nucleo as target     # pixhawk or nucleo

if __name__ == "__main__":
    target.do_handshake()

    while(1):
        joy.joystick_update()
        """ Ardusub/Nucleo expect pitch value [0 (max reverse),1000 (max forward)] and yaw value [-1000 (max right), 1000 (max left)]"""
        yaw = int(-joy.axes[0]*1000)
        pitch = int(-joy.axes[1]*500+500)
        target.send_cmd(pitch, yaw)
        target.get_feedback()
        time.sleep(0.1)