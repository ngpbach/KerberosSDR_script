import time
import sys
import serial
import json
import atexit
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

try:
    ser = serial.Serial("/dev/serial/by-id/usb-STMicroelectronics_STM32_STLink_066DFF313331464257022836-if02", 115200)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
except serial.SerialException as msg:
    log.error("msg")
    sys.exit()

def terminate():
    ser.write(b'\n')    # write one endline char to make sure fgets won't hang on nucleo
    ser.close()
    log.info("Exit program")

atexit.register(terminate)



heartbeat = 0
sender = "groundpc"     # set this string to id where the script is run

def _serialize_json(obj):
    obj["sender"] = sender
    obj["target"] = "nucleo"
    try:
        text = json.dumps(obj) + '\n' # very important to have endline char, otherwise fgets() block waiting until endline
        return text
        # log.debug("Sending:", text)
    except TypeError as msg:
        log.error(msg)

def arm():
    global heartbeat
    request = {"type":"handshake","arm":True}
    packet = {}
    hearbeat = 0
    ser.reset_input_buffer()
    while heartbeat < 1:    # handshake until receive 5 acks
        log.info("Waiting for nucleo handshake")
        ser.write(_serialize_json(request).encode())
        get_feedback(timeout=10)
    
    log.info("Arming success.")

def send_cmd(pitch, yaw):
    """ Nucleo expect pitch value [-1000 (max reverse),1000 (max forward)] and yaw value [-1000 (max right), 1000 (max left)]"""
    global heartbeat
    cmd = {"type":"cmd", "pitch":pitch,"yaw":yaw}
    message = _serialize_json(cmd)
    ser.write(message.encode())

def get_feedback(timeout=0.1):
    ser.timeout = timeout
    global heartbeat
    text = ser.readline()
    # log.debug("Received:", text)
    if not text:
        return
    try:
        packet = json.loads(text.decode())
        if "type" in packet:
            if  packet["type"] == "log":
                logfunction = eval("log."+ packet["level"])
                logfunction("[%s]%s\nEcho:'%s'", packet["sender"], packet["log"], packet["echo"])

            elif packet["type"] == "ack":
                heartbeat += 1

            elif packet["type"] == "data":
                heartbeat += 1
                return packet

            else:
                log.debug("Uknown packet type")
            

    except json.JSONDecodeError:
        log.warning("Unexpected or corrupted msg\nMessage: %s", text)
        
def disarm():
    cmd = {"disarm":True}
    message = _serialize_json(cmd)
    ser.write(message.encode())

if __name__ == "__main__":
    arm()

    for i in range(50):     # try running 5 secs
        send_cmd(600,0)
        get_feedback()
        time.sleep(0.1)
        log.debug("Heartbeat %d", heartbeat)

    disarm()
    