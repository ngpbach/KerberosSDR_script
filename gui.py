#!/usr/bin/env python3

import serial
import time
import signal
import atexit
import PySimpleGUI as sg
import json
import threading
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.DEBUG)

try:
    import joystick as joy
except Exception as msg:
    raise


""" LORA serial settings """
DEVICE = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0"       # requires platformio UDEV
BAUD = 115200    # baud of LORA UART
# DEVICE = "./pttyin"

try:
    ser = serial.Serial(DEVICE, BAUD, timeout=0.1)
    time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
    ser.reset_input_buffer()
except serial.SerialException as msg:
    log.error(msg)
    raise    

def terminate():
    ser.close()
    exit()

atexit.register(terminate)

def handler(signal_received, frame):
    terminate()

# Tell Python to run the handler() function when SIGINT is recieved
signal.signal(signal.SIGINT, handler) # ctlr + c
signal.signal(signal.SIGTSTP, handler) # ctlr + z
     
WHOAMI = "gcs"
TARGET = "pi"

def send_command(cmd, params={}):
    try:
        tries = 5
        packet = {}
        # Reducing message size to to low serial bandwidth
        # packet["origin"] = WHOAMI
        # packet["target"] = TARGET
        packet["type"] = "cmd"
        packet["cmd"] = cmd
        packet.update(params)
        message = json.dumps(packet, separators=(',', ':')) + '\n'
        # log.debug("Sending: %s", message)
        read_mutex.acquire()
        ser.write(message.encode())
        time.sleep(1)
        for i in range(tries):
            packet = get_feedback("ack")
            if packet is not None:
                break
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

read_mutex = threading.Lock()
buffer = ''
def read_serial():
    global buffer
    if ser.in_waiting > 0:
        message = ser.readline().decode()
        if not message or message[-1] != '\n':
            buffer += message
            return
        else:
            message = buffer + message
            buffer = ''
            return message

def get_feedback(type="telem"):
    message = read_serial()
    if message:
        # log.debug(message)
        try:
            packet = json.loads(message)
            if packet.get("type") == type:
                return packet
    
        except UnicodeDecodeError:
            log.error("Gargabe characters received: %s", message)
        except json.JSONDecodeError:
            log.info(message)

layout = [[sg.Text('Buttons will attempt to send command to Pi through LORA uart, but might fail due to packet collision.\nAcked mean successful.\nNot acked mean unknown if successful or not.\nCheck the response message to confirm and only try again if it really failed.')],
          [sg.Button('Calibrate')],
          [sg.Button('ARM'), sg.Button('DISARM')],
          [sg.Checkbox('Joystick', key='JS', default=False, enable_events=True)],
          [sg.Text('Kp'), sg.Input(size=(6,1), key='Kp'), sg.Text('Ki'), sg.Input(size=(6,1), key='Ki'), sg.Text('Kd'), sg.Input(size=(6,1), key='Kd'), sg.Button('SetGains', disabled=False)],
          [sg.Text('Restart button will attemp to restart the control software on Pi')],
          [sg.Button('Restart'), sg.Button('RebootPi', disabled=True), sg.Button('StartPiSerialShell', disabled=True)],
          [sg.Text(size=(10,1), key='result')]]
  
window = sg.Window('Ground Control Station', layout)

js_event = threading.Event()
def joystick_thread():
    log.info("Hold LT and use left joystick to control.")
    
    while True:
        js_event.wait()
        joy.joystick_update()
        send_joystick(joy.axes, joy.btns)
        time.sleep(0.2)

def get_feedback_thread():
    while(1):
        packet = get_feedback()
        if packet:
            log.info(packet)
        time.sleep(1)

if __name__ == "__main__":
    joystick_task = threading.Thread(target=joystick_thread, daemon=True)
    get_feedback_task = threading.Thread(target=get_feedback_thread, daemon=True)
    joystick_task.start()
    get_feedback_task.start()


    while True:
        window.Refresh()
        event, input = window.read()
        # log.debug("{}, {}".format(event, input))
        
        if event == sg.WINDOW_CLOSED:
            window.close()
            break
        
        elif event == 'Calibrate':
            ack = send_command("sync")
            if ack:
                log.info("Kerberos Sync procedure started")
            else:
                log.warning('Sync command *might* have lost. Check reply from Pi ("Waiting for Hydra..." means its working)')

        elif event == 'SetGains':
            params = {"Kp":input.get('Kp') or 0, "Ki":input.get('Ki') or 0, "Kd":input.get('Kd') or 0}
            ack = send_command("tune", params )
            # log.debug("PID params sent: %s", params)

        elif event == 'ARM':
            params = {"arm":True}
            ack = send_command("arm", params)
            # send_joystick([0,0,1], [1,0])   # TODO: sending an Arm command rather than joystick

        elif event == 'DISARM':
            params = {"arm":False}
            ack = send_command("arm", params)
            if ack:
                window['result'].update("Acked")
            else:
                window['result'].update("Not acked")
            # send_joystick([0,0,1], [0,1])   # TODO: sending an Disarm command rather than joystick

        elif event == 'Restart':
            ack = send_command("restart")
            log.info("Sent signal to restart control software on Pi side")

        elif event == "StartPiSerialShell":
            """ For turning of Pi's relay server and turn on serial terminal mode """
            ack = send_command("exit")

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
