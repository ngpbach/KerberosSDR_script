#!/usr/bin/env python3
import time
import sys
from pymavlink import mavutil
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

# Create the connection
master = mavutil.mavlink_connection("/dev/ttyACM0", baud=115200)


armed = False

def arm():
    # Wait a heartbeat before sending commands
    master.wait_heartbeat()

    # Choose a mode
    mode = 'MANUAL'

    # Get mode ID
    mode_id = master.mode_mapping()[mode]

    # Set new mode
    master.mav.set_mode_send(
        master.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id)

    # https://mavlink.io/en/messages/common.html
    # Arm
    armed = master.arducopter_arm()

    if armed:
        log.info("Arming success.")
    else:
        log.info("Arming failed")


def send_cmd(pitch, yaw):
    # https://mavlink.io/en/messages/common.html#MANUAL_CONTROL
    # Warning: Because of some legacy workaround, z will work between [0-1000]
    # where 0 is full reverse, 500 is no output and 1000 is full throttle.
    # x,y and r will be between [-1000 and 1000].
    master.mav.manual_control_send( master.target_system,
                                    pitch,
                                    0,
                                    yaw,
                                    500,
                                    0)

def get_feedback():
    # update arm status
    pass

def disarm():
    armed = not master.arducopter_disarm()
    if not armed:
        log.info("Disarming success.")
    else:
        log.warn("Disarming failed")

if __name__ == "__main__":
    arm()

    for i in range(50): # try running 5 secs
        send_cmd(100,0)
        get_feedback()
        time.sleep(0.1)

    disarm()
