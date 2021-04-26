import time
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)
import serial
import json

sender = "groundpc"     # set this string to id where the script is run

ser = serial.Serial("/dev/serial/by-id/usb-STMicroelectronics_STM32_STLink_066DFF313331464257022836-if02", 115200)
heartbeat = 0

def _serialize_json(obj):
    obj["sender"] = sender
    obj["target"] = "nucleo"
    return json.dumps(obj) + '\n'   # very important to have endline char, otherwise fgets() block waiting until endline

def do_handshake():
    ser.timeout = 10
    request = {"arm":True}
    reply = {}
    while not ("ack" in reply):
        log.info("Waiting for nucleo handshake")
        ser.reset_input_buffer()
        ser.write(_serialize_json(request).encode())
        text = ser.readline().decode()
        if not text:
            log.warning("Empty string received")
            continue
        try:
            reply = json.loads(text)
        except json.JSONDecodeError:
            log.warning("Unexpected or corrupted msg\nMessage: %s", text)
            continue
    
    if (reply["ack"]):
        log.info("Handshake success. %s", text)

def send_cmd(pitch, yaw):
    """ Nucleo expect pitch value [0 (max reverse),1000 (max forward)] and yaw value [-1000 (max right), 1000 (max left)]"""
    global heartbeat
    cmd = {"pitch":pitch,"yaw":yaw}
    message = _serialize_json(cmd)
    log.info(message)
    ser.write(message.encode())

def get_feedback():
    global heartbeat
    ser.timeout = 0
    text = ser.readline().decode()
    if not text:
        return

    try:
        reply = json.loads(text)
    except json.JSONDecodeError:
        log.warn("Unexpected or corrupted msg\nMessage: %s", text)
        return
    
    if ("log" in reply):
        logfunction = eval("log."+ reply["level"])
        logfunction("[%s]%s\nEcho:'%s'", reply["sender"], reply["log"], reply["echo"])

    if ("ack" in reply):
        heartbeat += 1

    log.info("Heartbeat %d", heartbeat)

def disarm():
    cmd = {"disarm":True}
    message = _serialize_json(cmd)
    log.info(message)
    ser.write(message.encode())

if __name__ == "__main__":
    do_handshake()

    for i in range(50):     # try running 5 secs
        send_cmd(600,0)
        get_feedback()
        time.sleep(0.1)

    disarm()
    