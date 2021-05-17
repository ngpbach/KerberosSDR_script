#!/usr/bin/env python3

import serial
import time
import signal
import atexit
import PySimpleGUI as sg
import json
import threading
import logging as log

"""
Set up joystick
"""
js_unavailable = True
try:
    import joystick as joy
    js_unavailable = False

except Exception as msg:
    log.warning("No Joystick available, disable Joystick function\n")

""" 
Setup LORA UART 
"""
DEVICE = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0"       # requires platformio UDEV
BAUD = 115200    # baud of LORA UART
# DEVICE = "./pttyin"

try:
    ser = serial.Serial(DEVICE, BAUD, timeout=1)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
    ser.reset_input_buffer()
except Exception as msg:
    log.error("Lora UART module not available, exiting\n")
    # log.error(msg)
    raise    

""" 
Handle exit events cleanly 
"""
def terminate():
    ser.close()
    exit()

atexit.register(terminate)

def handler(signal_received, frame):
    terminate()

# Tell Python to run the handler() function when SIGINT is recieved
signal.signal(signal.SIGINT, handler) # ctlr + c
signal.signal(signal.SIGTSTP, handler) # ctlr + z


""" 
Setup main GUI window 
"""
layout = [[sg.Text('Buttons will attempt to send command to Pi through LORA uart, but might fail due to packet collision.\nAcked mean successful.\nNot acked mean unknown if successful or not.\nCheck the response message to confirm and only try again if it really failed.')],
          [sg.Button('Calibrate')],
          [sg.Button('ARM'), sg.Button('DISARM')],
          [sg.Checkbox('Joystick', key='JS', default=False, enable_events=True, disabled=js_unavailable)],
          [sg.Text('Kp'), sg.Input(size=(6,1), key='Kp'), sg.Text('Ki'), sg.Input(size=(6,1), key='Ki'), sg.Text('Kd'), sg.Input(size=(6,1), key='Kd'), sg.Button('SetGains', disabled=False)],
          [sg.Text('Restart button will attemp to restart the control software on Pi')],
          [sg.Button('Restart'), sg.Button('RebootPi', disabled=True), sg.Button('StartPiSerialShell', disabled=True)],
          [sg.Text("Ack:"), sg.Text(size=(10,1), key='result')],
          [sg.Text("Feedback:")],
          [sg.Output(size=(200, 20), font=("roboto", 11), key='log')]]
  
window = sg.Window(title='Ground Control Station', layout=layout, finalize=True)

""" 
Setup logger 
"""
class LogHandler(log.StreamHandler):
    def __init__(self):
        log.StreamHandler.__init__(self)

    def emit(self, record):
        window['log'].update(value=record)

logger = log.StreamHandler()
logger.setLevel(log.DEBUG)
logger.setFormatter(log.Formatter('[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s'))
log.getLogger('').addHandler(logger)

"""
Helper functions
"""
WHOAMI = "gcs"
TARGET = "pi"



read_mutex = threading.Lock()   # mutex to make sure ack can be read by proper thread
def send_command(cmd, params={}, signal=True):
    try:

        tries = 5
        packet = {}
        # Reducing message size to save serial bandwidth
        # packet["origin"] = WHOAMI
        # packet["target"] = TARGET
        packet["type"] = "cmd"
        packet["cmd"] = cmd
        packet.update(params)
        message = json.dumps(packet, separators=(',', ':')) + '\n'
        # log.debug("Sending: %s", message)

        read_mutex.acquire()
        ser.reset_input_buffer()

        if signal:
            reply = None
            for i in range (tries):
                if reply == b'\n':
                    break
                else:
                    ser.write(b'\n')        # empty message to signal real messages coming next
                    reply = get_feedback()

        ser.write(message.encode())

        packet = get_feedback("ack")

        read_mutex.release()

        if packet and packet.get("cmd") == cmd:
            log.info("Command was acknowleged properly.")
            return True
        else:
            log.warning("Command was not acknowleged properly.")
            return False

    except TypeError as msg:
        log.error(msg)

def send_joystick(axes, btns):
    try:
        packet = {}
        # Reducing message size low serial bandwidth
        # packet["origin"] = WHOAMI
        # packet["target"] = TARGET
        packet["type"] = "js"
        packet["ax"] = [round(num, 3) for num in axes[0:3]]      # only need 3 axes, with 3 decimal places
        packet["bt"] = btns[0:2]      # only need 2 buttons
        message = json.dumps(packet) + '\n'
        log.debug("Sending: %s", message)
        ser.write(message.encode())

    except TypeError as msg:
        log.error(msg)

# buffer = ''
# def read_serial():
    # global buffer
    # if ser.in_waiting > 0:
    #     message = ser.readline()
    #     if not message or message[-1] != b'\n':
    #         buffer += message
    #         return
    #     else:
    #         message = buffer + message
    #         buffer = ''
    #         return message

def get_feedback(type="raw"):
    message = ser.readline()
    if message:
        log.debug(message)
        if type == "raw":
            return message

        try:
            packet = json.loads(message.decode())
            if packet.get("type") == type:
                return packet
    
        except UnicodeDecodeError:
            log.error("Gargabe characters received: %s", message)
        except json.JSONDecodeError:
            log.info("Packet received corrupted")

"""
Threads function
"""
js_event = threading.Event()
def joystick_thread():
    if js_unavailable:
        return

    log.info("Hold LT and use left joystick to control.")
    
    while True:
        js_event.wait()
        joy.joystick_update()
        send_joystick(joy.axes, joy.btns)
        time.sleep(0.2)

def get_feedback_thread():
    while(1):
        read_mutex.acquire()
        packet = get_feedback("telem")
        read_mutex.release()
        if packet:
            # log.info(packet)
            pass

        time.sleep(1)

"""
Main loop
"""
if __name__ == "__main__":
    joystick_task = threading.Thread(target=joystick_thread, daemon=True)
    get_feedback_task = threading.Thread(target=get_feedback_thread, daemon=True)
    joystick_task.start()
    get_feedback_task.start()
    
    ack = False
    while True:
        window.Refresh()
        event, input = window.read()
        # log.debug("{}, {}".format(event, input))
        
        if event == sg.WINDOW_CLOSED:
            window.close()
            break
        
        elif event == 'Calibrate':
            ack = send_command("sync", signal=True)
            # if ack:
            #     log.info("Kerberos Sync procedure started")
            # else:
            #     log.warning('Sync command *might* have lost. Check reply from Pi ("Waiting for Hydra..." means its working)')

        elif event == 'SetGains':
            params = {"Kp":input.get('Kp') or 0, "Ki":input.get('Ki') or 0, "Kd":input.get('Kd') or 0}
            ack = send_command("tune", params, signal=True)
            # log.debug("PID params sent: %s", params)

        elif event == 'ARM':
            params = {"arm":True}
            ack = send_command("arm", params, signal=True)
            # send_joystick([0,0,1], [1,0])
        elif event == 'DISARM':
            params = {"arm":False}
            ack = send_command("arm", params, signal=True)
            # send_joystick([0,0,1], [0,1])

        elif event == 'Restart':
            ack = send_command("restart", signal=True)
            # log.info("Sent signal to restart control software on Pi side")

        elif event == "StartPiSerialShell":
            """ For turning of Pi's relay server and turn on serial terminal mode """
            ack = send_command("exit", signal=True)

        elif event == "RebootPi":
            # Pi unable to reboot properly. Problem with Pi hang if rebooting with Kerberos backfeed power into USB port
            ack = send_command("reboot")
          
        elif input["JS"]:
                log.info("Using Joystick")
                js_event.set()
            
        elif not input["JS"]:
                log.info("Stop using Joystick")
                js_event.clear()
    

        if ack:
            window['result'].update("Acked")
        else:
            window['result'].update("Not acked")
