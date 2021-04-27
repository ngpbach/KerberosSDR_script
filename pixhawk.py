#!/usr/bin/env python3
import time
import sys
from pymavlink import mavutil

# Create the connection
master = mavutil.mavlink_connection("/dev/ttyACM0", baud=115200)

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
    master.arducopter_arm()

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
    pass

def disarm():
    master.arducopter_disarm()

if __name__ == "__main__":
    arm()

    for i in range(50): # try running 5 secs
        send_cmd(300,0)
        get_feedback()
        time.sleep(0.1)

    disarm()
