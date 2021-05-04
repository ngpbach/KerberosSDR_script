#!/usr/bin/env python3
import time
import sys
from pymavlink import mavutil
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)



""" Pixhawk USB connection settings """
DEVICE = "/dev/serial/by-id/usb-ArduPilot_Pixhawk1_360027001051303239353934-if00"
BAUD = 115200

class Pixhawk:

    def __init__(self, DEVICE, BAUD):
        self.armed = False
        heartbeat = 0
        master = mavutil.mavlink_connection(DEVICE, BAUD)

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

        manual = get_ack()

        if manual:
            # https://mavlink.io/en/messages/common.html
            # Arm
            master.arducopter_arm()
            self.armed = get_ack()
            if self.armed:
                log.info("Arming success.")
            else:
                log.info("Arming failed")
        else:
            log.info("Arming failed")



    def disarm():
        self.armed = master.arducopter_disarm()
        self.armed = not get_ack()

        if not self.armed:
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
        global heartbeat
        try:
            message = master.recv_match(blocking=True, timeout=1).to_dict()
            if message['mavpackettype'] == 'HEARTBEAT':
                if message['system_status'] == 3:
                    self.armed = False
                    log.info("Pixhawk ready, waiting to be self.armed")

                if message['system_status'] == 4:
                    self.armed = True

                else:
                    self.armed = False
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
    target = pixhawk(DEVICE, BAUD)
    target.arm()
    for i in range(5):
        target.send_cmd(200,0)
        target.get_feedback()
        time.sleep(1)

    disarm()

