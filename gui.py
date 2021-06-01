#!/usr/bin/env python3

import serial
from serial.tools import miniterm
import time
import socket
import signal
import atexit
import PySimpleGUI as sg
import json
import threading
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

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
lora_unavailable = True
DEVICE = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0"       # requires platformio UDEV
BAUD = 115200    # baud of LORA UART

class Lora:
    def __init__(self):
        global lora_unavailable
        self.telem_packet = None
        self.read_mutex = threading.Lock()   # mutex to make sure ack won't be consumed by another thread
        self.send_mutex = threading.Lock()   # mutex to make sure only one command is being sent when waiting for ack
        self.js_signal = threading.Event()
        try:
            self.ser = serial.Serial(DEVICE, BAUD, timeout=2)
            time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
            self.ser.reset_input_buffer()
            lora_unavailable = False
        except Exception as msg:
            log.warning("Lora UART module not available, LORA option disabled\n")
            # log.error(msg)


    def send_command(self, cmd, params={}, signal=True):
        try:

            tries = 3
            packet = {}
            # Reducing message size to save serial bandwidth
            # packet["origin"] = WHOAMI
            # packet["target"] = TARGET
            packet["type"] = "cmd"
            packet["cmd"] = cmd
            packet.update(params)
            message = json.dumps(packet, separators=(',', ':')) + '\n'
            # log.debug("Sending: %s", message)

            self.read_mutex.acquire()
            self.send_mutex.acquire()
            self.ser.reset_input_buffer()

            if signal:
                reply = None
                for i in range (tries):
                    if reply == b'\n':
                        break
                    else:
                        self.ser.write(b'\n')        # empty message to signal real messages coming next
                        reply = self.get_feedback(label="Handshake")

            self.ser.write(message.encode())
            packet = self.get_feedback("ack", label="Ack")

            self.read_mutex.release()
            self.send_mutex.release()

            if packet and packet.get("cmd") == cmd:
                log.info("Command was acknowleged properly.")
                return True
            else:
                log.warning("Command was not acknowleged properly.")
                return False

        except TypeError as msg:
            log.error(msg)
        
    def get_feedback(self, type="raw", label="Serial"):
        try:
            message = self.ser.readline()
            if message:
                log.debug(message)
                if type == "raw":
                    return message
                else:
                    packet = json.loads(message.decode())
                    if packet.get("type") == type:
                        return packet
            else:
                log.debug("%s read timed out.", label)

        except UnicodeDecodeError:
            log.error("Gargabe characters received: %s", message)
        except json.JSONDecodeError:
            # log.debug("Packet received corrupted")
            pass
        except Exception as msg:
            log.debug(msg)


    def send_joystick(self, axes, btns):
        try:
            packet = {}
            # Reducing message size low serial bandwidth
            # packet["origin"] = WHOAMI
            # packet["target"] = TARGET
            packet["type"] = "js"
            packet["ax"] = [round(num, 3) for num in axes[0:3]]      # only need 3 axes, with 3 decimal places
            packet["bt"] = btns[0:2]      # only need 2 buttons
            message = json.dumps(packet) + '\n'
            # log.debug("Sending: %s", message)
            self.ser.write(message.encode())

        except TypeError as msg:
            log.error(msg)

    
    def get_feedback_thread(self):
        while(1):
            self.read_mutex.acquire()
            self.telem_packet = self.get_feedback("telem", label="Telem")
            self.read_mutex.release()

            time.sleep(1)

    def joystick_thread(self):
        if js_unavailable:
            return

        log.info("Hold LT and use left joystick to control.")
        
        while True:
            self.js_signal.wait()
            joy.joystick_update()
            self.send_mutex.acquire()
            self.send_joystick(joy.axes, joy.btns)
            self.send_mutex.release()
            time.sleep(0.2)

    def close(self):
        self.read_mutex.acquire()    # lock read threads
        self.send_mutex.acquire()    # lock write threads
        # ser.write(b"\n")
        self.ser.close()

lora = Lora()

""" 
Setup UDP
"""
IP_BROADCAST = "192.168.43.255"
IP_ANY = "0.0.0.0"
PORT_GUI = 5005
PORT_RELAY = 5000

class UDP:
    def __init__(self):
        self.telem_packet = None
        self.js_signal = threading.Event()
        self.read_mutex = threading.Lock()   # mutex to make sure ack won't be consumed by another thread
        self.send_mutex = threading.Lock()   # mutex to make sure only one command is being sent when waiting for ack

        try:
            self.sock = socket.socket(socket.AF_INET,   # Internet
                                    socket.SOCK_DGRAM)  # UDP
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind((IP_ANY, PORT_GUI))
            self.sock.settimeout(1)

        except Exception as msg:
            log.error(msg)

    def send_command(self, cmd, params={}, signal=False, tries=2):
        try:
            packet = {}
            packet["type"] = "cmd"
            packet["cmd"] = cmd
            packet.update(params)
            message = json.dumps(packet, separators=(',', ':')) + '\n'
            # log.debug("Sending: %s", message)

            self.send_mutex.acquire()
            self.read_mutex.acquire()
            # old_timeout = self.sock.gettimeout()
            # self.sock.settimeout(1)
         
            if signal:
                for i in range(tries):
                    self.sock.sendto(b'\n', (IP_BROADCAST, PORT_RELAY))        # empty message to signal real messages coming next
                    reply = self.get_feedback(label="Handshake", tries=2)
                    if reply == b'\n':
                        break
                       
            
            self.sock.sendto(message.encode(), (IP_BROADCAST, PORT_RELAY))            
            reply = self.get_feedback("ack", label="Ack", tries=2)
                
            # self.sock.settimeout(old_timeout)
            # self.send_mutex.release()
            # self.read_mutex.release()
            

            if reply and reply.get("cmd") == cmd:
                log.info("Command was acknowleged properly.")
                return True
            else:
                log.warning("Command was not acknowleged properly.")
                return False

        except TypeError as msg:
            log.error(msg)
        finally:
            # self.sock.settimeout(old_timeout)
            self.send_mutex.release()
            self.read_mutex.release()
         
    def send_joystick(self, axes, btns):
        try:
            packet = {}
            # Reducing message size low serial bandwidth
            # packet["origin"] = WHOAMI
            # packet["target"] = TARGET
            packet["type"] = "js"
            packet["ax"] = [round(num, 3) for num in axes[0:3]]      # only need 3 axes, with 3 decimal places
            packet["bt"] = btns[0:2]      # only need 2 buttons
            message = json.dumps(packet) + '\n'
            # log.debug("Sending: %s", message)
            self.sock.sendto(message.encode(), (IP_BROADCAST, PORT_RELAY))  

        except TypeError as msg:
            log.error(msg)   
     
    def get_feedback(self, type="raw", label="UDP", tries=1):
        for i in range(tries):
            try:
                message, addr = self.sock.recvfrom(1024)
                if message:
                    log.debug(message)
                    if type == "raw":
                        return message
                    else:
                        packet = json.loads(message.decode())
                        if packet.get("type") == type:
                            return packet

                else:
                    log.debug("%s read timed out.", label)

            except socket.timeout:
                log.debug("%s read timed out.", label)
            except UnicodeDecodeError:
                log.error("Gargabe characters received: %s", message)
            except json.JSONDecodeError:
                # log.debug("Packet received corrupted")
                pass
            except Exception as msg:
                log.debug(msg)

    def get_feedback_thread(self):
        while(1):
            self.read_mutex.acquire()
            self.telem_packet = self.get_feedback("telem", label="Telem")
            self.read_mutex.release()
            time.sleep(0.1)

    def joystick_thread(self):
        if js_unavailable:
            return

        log.info("Hold LT and use left joystick to control.")
        
        while True:
            self.js_signal.wait()
            joy.joystick_update()
            self.send_joystick(joy.axes, joy.btns)
            time.sleep(0.1)

udp = UDP()

"""
Helper functions
"""
def update_gui(window, packet):
    try:
        window["heartbeat"].update(packet.get("heartbeat"))
        window["arm"].update(packet.get("arm"))
        window["pitch"].update(packet.get("effort(p,y)")[0])
        window["yaw"].update(packet.get("effort(p,y)")[1])
        window["bearing"].update(packet.get("bearing"))
        window["confident"].update(packet.get("confident"))
        window["vision"].update(packet.get("vision"))
        window["distance"].update(packet.get("distance"))
    except TypeError as msg:
        log.debug(msg)
    

""" 
Setup main GUI window 
"""
demo_mode = False
sg.ChangeLookAndFeel("Reddit")

layout = [
          [sg.Button("Calibrate"), sg.Frame("Calibrated", [[sg.Text(size=(10,1), text_color="red", key="calibrated")]])],
          [sg.Button("ARM"), sg.Button("DISARM")],
          [sg.Checkbox("Joystick", key="JS", default=demo_mode, disabled=js_unavailable)],
          [sg.Button("Restart"), sg.Text("Attemp to restart the control software on Pi")],
          [sg.Button("RebootPi"), sg.Text("Attempt to reboot operating system on WaterPi")],
          [sg.Button("StartPiSerialShell", disabled=demo_mode), sg.Text("Turn off WaterPi relay server and turn on WaterPi Serial Shell for troubleshooting")],
          [sg.Frame(
            "Tuning",
            [[
            sg.Text("Kp"), sg.Input(size=(6,1), key="Kp"), sg.Text("Ki"), sg.Input(size=(6,1), key="Ki"), sg.Text("Kd"), sg.Input(size=(6,1), key="Kd"), sg.Button("SetGains", disabled=demo_mode),
            sg.Text("Min Power"), sg.Input(size=(6,1), key="minpow"), sg.Text("Min Confidence"), sg.Input(size=(6,1), key="minconf"), sg.Button("SetThresholds", disabled=demo_mode)
            ]]
            )
          ],
          [sg.Frame("Heartbeat", [[sg.Text(size=(10,1), text_color="red", key="heartbeat")]]), 
           sg.Frame("Arm", [[sg.Text(size=(10,1), text_color="red", key="arm")]]), 
           sg.Frame("Yaw effort", [[sg.Text(size=(10,1), text_color="red", key="yaw")]]), 
           sg.Frame("Pitch effort", [[sg.Text(size=(10,1), text_color="red", key="pitch")]]),
           sg.Frame("Radio bearing", [[sg.Text(size=(10,1), text_color="red", key="bearing")]]),
           sg.Frame("Confident", [[sg.Text(size=(10,1), text_color="red", key="confident")]]),
           sg.Frame("Vision bearing", [[sg.Text(size=(10,1), text_color="red", key="vision")]]),
           sg.Frame("Vision distance", [[sg.Text(size=(10,1), text_color="red", key="distance")]])
          ],
          [sg.Frame("Log", [[sg.Output(size=(125, 5), key="log")]])]
          ]

window = sg.Window(title="Ground Control Station", layout=layout, default_element_size=(10,1), auto_size_buttons=True, auto_size_text=True, finalize=True)

event, input = sg.Window("Comm link", keep_on_top=True, layout=[[sg.Button("WIFI (UDP)"), sg.Button("LORA (UART)", disabled=lora_unavailable)]]).read(close=True)

if event == "LORA":
    comm = lora
    sg.popup("Each button attempts to send a command to WaterPi through LORA uart, but might fail due to packet collision.\n"
          "Acked mean successful.\nNot acked mean unknown if successful or not.\n"
          "Check the response message to confirm and try again if it really failed.", keep_on_top=True, title="Attention")
else:
    comm = udp

    
""" 
Setup logger 
"""
class LogHandler(log.StreamHandler):
    def __init__(self):
        log.StreamHandler.__init__(self)

    def emit(self, record):
        window["log"].update(value=record)

logger = log.StreamHandler()
logger.setLevel(log.DEBUG)
logger.setFormatter(log.Formatter('[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s'))
log.getLogger('').addHandler(logger)

""" 
Handle exit events cleanly 
"""
def terminate():
    window.close()
    # lora.ser.close()
    exit()

atexit.register(terminate)

def handler(signal_received, frame):
    terminate()

# Tell Python to run the handler() function when SIGINT is recieved
signal.signal(signal.SIGINT, handler) # ctlr + c
signal.signal(signal.SIGTSTP, handler) # ctlr + z

"""
Main loop
"""
if __name__ == "__main__":
    joystick_task = threading.Thread(target=comm.joystick_thread, daemon=True)
    get_feedback_task = threading.Thread(target=comm.get_feedback_thread, daemon=True)
    joystick_task.start()
    get_feedback_task.start()
    
    ack = False
    while True:
        if comm.telem_packet:
            update_gui(window, comm.telem_packet)
            
        # window.Refresh()
        event, input = window.read(timeout=1000)
        # log.debug("{}, {}".format(event, input))
        
        if event == sg.WINDOW_CLOSED:
            window.close()
            break
        
        elif event == "Calibrate":
            sg.popup("Calibration is required everytime WaterPi software has been reset.\n"
                     "Make sure that all antennas are disconnected (but leave the cables connected)\n"
                     "and all nearby beacons transmitting around 121.65Mhz are off before calibrating.", keep_on_top=True, title="Attention")

            ack = comm.send_command("sync")
            progress_window = sg.Window("Progress", layout=[[sg.Text("Syncing takes approximately 60 seconds")], 
                                                            [sg.ProgressBar(100, size=(50, 20), key='progress')]], finalize=True, keep_on_top=True)
            if ack:
                comm.read_mutex.acquire()
                
                for i in range (100):    # TODO: define a duration
                    progress_window["progress"].update(i)
                    packet = comm.get_feedback("progress", label="progress")
                    if packet and packet.get("progress") == 100:
                        progress_window["progress"].update(100)
                        progress_window.close()
                        break

                comm.read_mutex.release()
            else:
                log.warning("Sync command *might* have lost. Check debug logs if sync process started")

        elif event == "SetGains":
            try:
                params = {"Kp":float(input.get("Kp") or 0), "Ki":float(input.get("Ki") or 0), "Kd":float(input.get("Kd") or 0)}
                ack = comm.send_command("tune", params)
                # log.debug("PID params sent: %s", params)
            except Exception as msg:
                log.debug(msg)

        elif event == "SetThresholds":
            try:
                params = {"power":int(input.get("minpow") or 0), "conf":int(input.get("minconf") or 0)}
                ack = comm.send_command("threshold", params)
            except Exception as msg:
                log.debug(msg)

        elif event == "ARM":
            params = {"arm":True}
            ack = comm.send_command("arm", params)
            # send_joystick([0,0,1], [1,0])

        elif event == "DISARM":
            params = {"arm":False}
            ack = comm.send_command("arm", params)
            # send_joystick([0,0,1], [0,1])

        elif event == "Restart":
            ack = comm.send_command("restart")
            # log.info("Sent signal to restart control software on Pi side")

        elif event == "StartPiSerialShell":
            """ For turning of Pi"s relay server and turn on serial terminal mode """
            ack = comm.send_command("exit")
            if ack:
                window["log"].__del__() # work around pysimplegui Output bug not returning stdio
                window.close()
                comm.close()
                miniterm.main(DEVICE,BAUD)
                break

        elif event == "RebootPi":
            # Pi unable to reboot properly. Problem with Pi hang if rebooting with Kerberos backfeed power into USB port
            ack = comm.send_command("reboot")
          
        elif input["JS"]:
            if not comm.js_signal.is_set():
                log.info("Using Joystick. Feedback disabled")
                comm.js_signal.set()
            
        elif not input["JS"]:
            if comm.js_signal.is_set():
                log.info("Stop using Joystick")
                comm.js_signal.clear()
    
        if event != "__TIMEOUT__":
            if ack:
                sg.popup("Acked", keep_on_top=True)
            else:
                sg.popup("Not Acked", keep_on_top=True)
            
