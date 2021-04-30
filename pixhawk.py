#!/usr/bin/env python3
import time
import sys
from pymavlink import mavutil
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

""" Device specific settings """
# DEVICE = "/dev/serial/by-id/usb-ArduPilot_Pixhawk1_360027001051303239353934-if00"
# BAUD = 115200
DEVICE = "/dev/serial/by-id/usb-Silicon_Labs_CP2104_USB_to_UART_Bridge_Controller_01E97D63-if00-port0"
BAUD = 57200

# Create the connection
master = mavutil.mavlink_connection(DEVICE, BAUD)


armed = False

def arm():
    global armed
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
    armed = get_ack()

    if armed:
        log.info("Arming success.")
    else:
        log.info("Arming failed")


def disarm():
    global armed
    armed = master.arducopter_disarm()
    armed = not get_ack()

    if not armed:
        log.info("Disarming success.")
    else:
        log.warning("Disarming failed")

def get_ack():
    # Wait for ACK command
    ack_msg = master.recv_match(type='COMMAND_ACK', blocking=True)
    ack_msg = ack_msg.to_dict()

    if ack_msg['result'] == 0:
        return True

    log.debug(mavutil.mavlink.enums['MAV_RESULT'][ack_msg['result']].description)

def send_cmd(pitch, yaw):
    # https://mavlink.io/en/messages/common.html#MANUAL_CONTROL
    # Warning: Because of some legacy workaround, z will work between [0-1000]
    # where 0 is full reverse, 500 is no output and 1000 is full throttle.
    # x,y and r will be between [-1000 and 1000].
    master.mav.manual_control_send( master.target_system,
                                    pitch,
                                    0,
                                    500,
                                    yaw,
                                    0)



if __name__ == "__main__":
    arm()
    send_cmd(200,0)
    time.sleep(5)

    disarm()

