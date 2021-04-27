import time
import sys
import serial
import json
import atexit
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

try:
    _ser = serial.Serial("/dev/serial/by-id/usb-STMicroelectronics_STM32_STLink_066DFF313331464257022836-if02", 115200)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
    _ser.reset_input_buffer()
except serial.SerialException as msg:
    log.error("msg")
    sys.exit()

def terminate():
    _ser.write(b'\n')    # work around: write one termination char to make sure fgets won't hang on nucleo
    _ser.close()
    log.info("Serial closed")

atexit.register(terminate)

armed = False
heartbeat = 0
_sender = "pi"     # set this string to id where the script is run

def _unblock():
    """ 
    A work around for Nucleo blocking fgets(). If erronous string (no termination) was sent through serial, fgets() would block the control loop.
    Send a endline char to unblock fgets. Will implement thread for fgets in the future.
    """
    _ser.write(b'\n')

def _serialize_json(obj):
    obj["sender"] = _sender
    obj["target"] = "nucleo"
    try:
        text = json.dumps(obj) + '\n' # very important to have endline char, otherwise fgets() block waiting until endline
        return text
        # log.debug("Sending:", text)
    except TypeError as msg:
        log.error(msg)

def arm():
    global armed
    if not armed:
        global heartbeat
        cmd = {"type":"cmd","arm":True}
        packet = _serialize_json(cmd).encode()

        log.info("Waiting for nucleo handshake")
        while not armed:
            _ser.write(packet)
            get_feedback(timeout=10)
        
        if armed:
            log.info("Arming success.")
        else:
            log.info("Arming failed")
        
  
def disarm():
    global armed
    if armed:
        cmd = {"type":"cmd","disarm":True}
        packet = _serialize_json(cmd).encode()
        while armed:
            _ser.write(packet)
            get_feedback(timeout=10)

        if not armed:
            log.info("Disarming success.")
        else:
            log.warn("Disarming failed")

def send_cmd(pitch, yaw):
    """ Nucleo expect pitch value [-1000 (max reverse),1000 (max forward)] and yaw value [-1000 (max right), 1000 (max left)]"""
    cmd = {"type":"cmd", "pitch":int(pitch),"yaw":int(yaw)}
    packet = _serialize_json(cmd).encode()
    _ser.write(packet)


def get_feedback(timeout=0.1):
    global armed
    global heartbeat
    _ser.timeout = timeout
    text = _ser.readline().decode()
    # log.debug("Received:", text)
    if not text:
        return
    try:
        packet = json.loads(text)
        
        if not "type" in packet:
            log.debug("No packet type")

        elif packet["type"] == "log":
            logfunction = eval("log."+ packet["level"])
            echo = "\nEcho:{}".format(packet["echo"]) if "echo" in packet else ""
            logfunction("[%s]%s%s", packet["sender"], packet["log"], echo)

        elif packet["type"] == "ack":
            armed = packet["arm"]

        elif packet["type"] == "data":
            return packet

        else:
            log.debug("Packet format correct but unknown packet type")

        heartbeat = packet["count"]
        
    except json.JSONDecodeError:
        log.warning("Unexpected or corrupted msg\nMessage: %s", text)
      



if __name__ == "__main__":
    arm()

    for i in range(50):     # try running 5 secs
        send_cmd(100,0)
        get_feedback()
        time.sleep(0.1)
        log.debug("heartbeat %d", heartbeat)

    disarm()
    