#!/usr/bin/env python3
import time
import sys
from pymavlink import mavutil
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

""" Device specific settings """
DEVICE = "/dev/serial/by-id/usb-ArduPilot_Pixhawk1_360027001051303239353934-if00"
BAUD = 115200
#DEVICE = "/dev/serial/by-id/usb-Silicon_Labs_CP2104_USB_to_UART_Bridge_Controller_01E97D63-if00-port0"
#BAUD = 57200

# Create the connection
master = mavutil.mavlink_connection(DEVICE, BAUD)


armed = False
heartbeat = 0

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

    manual = get_ack()

    if manual:
        # https://mavlink.io/en/messages/common.html
        # Arm
        master.arducopter_arm()
        armed = get_ack()
        if armed:
            log.info("Arming success.")
        else:
            log.info("Arming failed")
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
    try:
        ack_msg = master.recv_match(type='COMMAND_ACK', blocking=True).to_dict()
        if ack_msg['result'] == 0:
            return True
        else:
            log.debug(mavutil.mavlink.enums['MAV_RESULT'][ack_msg['result']].description)

    except KeyError as msg:
        log.error("Packet received has no [%s] key", msg)

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

def get_feedback():
    global armed
    global heartbeat
    try:
        message = master.recv_match(blocking=True, timeout=1).to_dict()
        if message['mavpackettype'] == 'HEARTBEAT':
            if message['system_status'] == 3:
                armed = False
                log.info("Pixhawk ready, waiting to be armed")

            if message['system_status'] == 4:
                armed = True

            else:
                armed = False
                log.error("Pixhawk automatically disarmed. Unknown reason")

            log.debug(mavutil.mavlink.enums['MAV_STATE'][message['system_status']].description)
            heartbeat += 1

        log.debug(message)

    except KeyError as msg:
        log.error("Packet received has no [%s] key", msg)
    # Request parameter
    # master.mav.param_request_list_send(
    #     master.target_system, master.target_component,
    # )

    # while(1):
    #     message = master.recv_match().to_dict()
    #     log.debug(message)
    #     time.sleep(0.01)
    # # log.debug('name: %s value:%d', message['param_id'], message['param_value'])



if __name__ == "__main__":
    arm()
    for i in range(5):
        send_cmd(200,0)
        get_feedback()
        time.sleep(1)

    disarm()

