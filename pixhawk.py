#!/usr/bin/env python3
import threading
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
        self.mutex = threading.Lock()
        self.armed = False
        self.heartbeat = 0
        self.master = mavutil.mavlink_connection(DEVICE, BAUD)

        # Wait a heartbeat before sending commands
        # self.mutex.acquire()
        # self.master.reboot_autopilot()
        # time.sleep(10)
        # self.master = mavutil.mavlink_connection(DEVICE, BAUD)
        self.master.wait_heartbeat()

        # Choose a mode
        mode = 'MANUAL'

        # Get mode ID
        mode_id = self.master.mode_mapping()[mode]

        # Set new mode
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id)

        ack = self.get_ack(mavutil.mavlink.MAVLINK_MSG_ID_SET_MODE, retry=3)
        # self.mutex.release()
        if ack:
            log.info("Manual mode success")
        else:
            log.info("Manual mode failed")

    def arm(self):

        # https://mavlink.io/en/messages/common.html
        # Arm
        self.mutex.acquire()
        self.master.arducopter_arm()
        self.armed = self.get_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, retry=3)
        self.mutex.release()

        if self.armed:
            log.info("Arming success.")
        else:
            log.info("Arming failed")



    def disarm(self):
        self.mutex.acquire()
        self.armed = self.master.arducopter_disarm()
        self.armed = not self.get_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, retry=3)
        self.mutex.release()

        if not self.armed:
            log.info("Disarming success.")
        else:
            log.warning("Disarming failed")

    def get_ack(self, cmd, retry=1):
        try:
            for i in range(retry):
                # Wait for ACK command
                    ack_msg = self.master.recv_match(type='COMMAND_ACK', blocking=True).to_dict()
                    if ack_msg["command"] == cmd and ack_msg['result'] == 0:
                        return True
                    else:
                        log.debug(mavutil.mavlink.enums['MAV_RESULT'][ack_msg['result']].description)

        except KeyError as msg:
            log.debug("Packet received has no [%s] key", msg)

        return False

    def send_cmd(self, pitch, yaw):
        # https://mavlink.io/en/messages/common.html#MANUAL_CONTROL
        # Warning: Because of some legacy workaround, z will work between [0-1000]
        # where 0 is full reverse, 500 is no output and 1000 is full throttle.
        # x,y and r will be between [-1000 and 1000].
        self.master.mav.manual_control_send( self.master.target_system,
                                        pitch,
                                        0,
                                        500,
                                        yaw,
                                        0)

    def get_feedback(self):
        try:
            self.mutex.acquire()
            message = self.master.recv_match(blocking=True, timeout=5).to_dict()
            if message['mavpackettype'] == 'HEARTBEAT':
                if message['system_status'] == 3:
                    self.armed = False
                    log.info("Pixhawk ready, waiting to be armed")

                if message['system_status'] == 4:
                    self.armed = True

                else:
                    self.armed = False

                log.debug(mavutil.mavlink.enums['MAV_STATE'][message['system_status']].description)
                self.heartbeat += 1

            log.debug(message)

        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)
        except AttributeError as msg:
            log.error(msg)
        finally:
            self.mutex.release()
        # Request parameter
        # self.master.mav.param_request_list_send(
        #     self.master.target_system, self.master.target_component,
        # )

        # while(1):
        #     message = self.master.recv_match().to_dict()
        #     log.debug(message)
        #     time.sleep(0.01)
        # # log.debug('name: %s value:%d', message['param_id'], message['param_value'])



if __name__ == "__main__":
    target = Pixhawk(DEVICE, BAUD)
    target.arm()
    for i in range(10):
        target.send_cmd(200,0)
        target.get_feedback()
        time.sleep(1)

    target.disarm()


