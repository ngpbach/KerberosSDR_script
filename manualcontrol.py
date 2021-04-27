#!/usr/bin/env python3

import time
try:
    import joystick as joy
except UserWarning as msg:
    log.warning(msg)
import nucleo as target     # pixhawk or nucleo
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

if __name__ == "__main__":
    while(1):
        joy.joystick_update()
        """ Ardusub/Nucleo expect pitch value [0 (max reverse),1000 (max forward)] and yaw value [-1000 (max right), 1000 (max left)]"""
        arm = joy.btns[0]
        disarm = joy.btns[1]
        yaw = int(-joy.axes[0]*1000)
        pitch = int(-joy.axes[1]*1000)
        
        if (arm == 1):
            if (pitch == 0 and yaw == 0):
                target.arm()
            else:
                log.info("Joystick Pitch and Yaw must be neutral for arming")

        if (disarm == 1):
            target.disarm()

        if (target._arm):
            target.send_cmd(pitch, yaw)

        target.get_feedback()
        time.sleep(0.1)