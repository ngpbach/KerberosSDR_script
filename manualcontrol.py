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
        js_active = joy.axes[5] > 0     # hold down RT button to use joystick
        if js_active:
            arm = joy.btns[0]
            disarm = joy.btns[1]
            yaw = int(-joy.axes[0]*1000)    # left stick left-right for yaw
            pitch = int(-joy.axes[1]*1000)  # left stick up-down for pich

            if (target.armed):
                target.send_cmd(pitch, yaw)

            if arm:      # press A to arm    
                if (pitch == 0 and yaw == 0):          
                    target.arm()
                else:
                    log.info("Joystick Pitch and Yaw must be neutral for arming")  

            if disarm:   # press B to disarm
                target.disarm()

                    
        


        target.get_feedback()
        time.sleep(0.1)