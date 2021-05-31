#!/usr/bin/env python3
"""
Act as relay server for the pi to compile and sort serial packet and send through UDP to the appropriate port, and vice versa
Swith to Pi serial console mode when commanded to
"""
import subprocess
from subprocess import PIPE, Popen

import os
import time
import threading
import atexit
import socket
import serial
import json
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.DEBUG)

cmd_start_console = 'sudo stty -F /dev/serial0 115200 && sudo systemctl start serial-getty@serial0.service'            # start the serial console when this program exit
cmd_stop_console = 'sudo systemctl stop serial-getty@serial0.service'            # stop the serial console when this program start
cmd_start_kerberos = '/home/bnguye14/Desktop/kerberos_scripts/start_kerberos_doa.sh'      # start the kerberos syncing procedure and then start DOA server
cmd_restart = '/home/pi/Desktop/kerberos_scripts/start_control.sh'

# subprocess.run(cmd_stop_console, shell=True)
# log.info("Relay server started. Serial console mode disable")

# def terminate():
#     subprocess.run(cmd_start_console, shell=True)
#     log.info("Relay server exiting. Serial console mode enable")

# atexit.register(terminate)

WHOAMI = "pi"
TARGET = "gcs"
PORT_RELAY = 5000
PORT_KERB = 5001
PORT_JS = 5002
PORT_CMD = 5003
PORT_VISION = 5004
PORT_GUI = 5005
LOCALHOST = "127.0.0.1"
IP_BROADCAST = "192.168.43.255"
IP_ANY = "0.0.0.0"

""" Device specific settings """
BAUD = 115200    # baud of LORA UART
DEVICE = "/dev/serial0"
# DEVICE = "./pttyout"

def demote(user_uid):
   def result():
      os.setuid(user_uid)
   return result

class RelayServer:
    """ Convenient class for forwarding JSON packet to the appropriate port """
    def __init__(self):
        # self.serial_idle = threading.Event()       # the LORA module corrupt message a lot if sending & receiving at the same time. Use Event to cease sending telem if start receiving command, and start sending telem once no longer receiving command
        # self.to_be_written_to_serial = None
        # try:
        #     self.ser = serial.Serial(DEVICE, BAUD, timeout=1)
        #     time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
        #     self.ser.reset_input_buffer()
        # except serial.SerialException as msg:
        #     log.error(msg)
        #     raise
        
        self.sock = socket.socket(socket.AF_INET,   # Internet
                                socket.SOCK_DGRAM)  # UDP
        self.sock.bind((IP_ANY, PORT_RELAY))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setblocking(True)
    
    # def process_serial(self):
    #     try:
    #         message = self.ser.readline()
    #         log.debug(message)
    #         if not message:
    #             self.serial_idle.set()
    #             # log.debug("serial_idle: Serial read timeout")
    #             return

    #         else:
    #             # Perform simple handshaking
    #             self.serial_idle.clear()
    #             tries = 5
    #             for i in range (tries):
    #                 if message == b'\n':      # empty message to signal real messages coming next
    #                     self.ser.write(b'\n')
    #                     message = self.ser.readline()
    #                 else:
    #                     break
                
    #             self.process(message)

    #     except Exception as msg:
    #         log.error(msg)
                    
    def process_udp(self):
        try:
            message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes    
            
            if message:
                # tries = 5
                # for i in range (tries):
                #     if message == b'\n':      # empty message to signal real messages coming next
                #         self.sock.sendto(b'\n', (IP_BROADCAST, PORT_GUI))
                #         message, addr = self.sock.recvfrom(1024)
                #     else:
                #         break
                self.process(message)

        except UnicodeDecodeError:
            log.error("Gargabe characters received: %s", message)
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)
    
    def process(self, message):
        try:
            log.debug(message)
            packet = json.loads(message.decode())

            if packet.get("type") == "telem":
                self.sock.sendto(message, (IP_BROADCAST, PORT_GUI))
                self.to_be_written_to_serial = message

            elif packet.get("type") == "js":
                self.sock.sendto(message, (LOCALHOST, PORT_JS))

            elif packet.get("type") == "cmd":
                # time.sleep(0.1)     # wait a little before sending ack

                if packet.get("cmd") == "arm":
                    self.send_ack("arm")
                    self.sock.sendto(message, (LOCALHOST, PORT_CMD))

                elif packet.get("cmd") == "tune":
                    self.send_ack("tune")
                    self.sock.sendto(message, (LOCALHOST, PORT_CMD))
                
                elif packet.get("cmd") == "threshold":
                    self.send_ack("threshold")
                    self.sock.sendto(message, (LOCALHOST, PORT_CMD))

                elif packet.get("cmd") == "sync":
                    self.send_ack("sync")
                    process = Popen(cmd_start_kerberos, preexec_fn=demote(1000), stdout=PIPE, stderr=PIPE, bufsize=1)

                    i = 0
                    for line in process.stdout:
                        i += 1
                        message = json.dumps({"info":line.decode()})
                        self.sock.sendto(message.encode(), (IP_BROADCAST, PORT_GUI))

                        message = json.dumps({"type":"progress","progress":i})
                        self.sock.sendto(message.encode(), (IP_BROADCAST, PORT_GUI))

                        # self.ser.write(line)
                        log.info(line.decode())

                        if "done" in line.decode():
                            message = json.dumps({"type":"progress","progress":100})
                            self.sock.sendto(message.encode(), (IP_BROADCAST, PORT_GUI))
                            break
                        
                    time.sleep(1)

                elif packet.get("cmd") == "exit":
                    self.send_ack("exit")
                    time.sleep(1)
                    exit(0)

                elif packet.get("cmd") == "restart":
                    self.send_ack("restart")
                    process = Popen(cmd_restart, stdout=PIPE, stderr=PIPE, bufsize=1)
                
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)

    def send_ack(self, cmd):
        packet={}
        packet["type"] = "ack"
        packet["cmd"] = cmd
        reply = (json.dumps(packet) + '\n')
        # self.ser.write(reply.encode())    # endline is important for framing
        self.sock.sendto(reply.encode(), (IP_BROADCAST, PORT_GUI))

    # def serial_processing_thread(self):
    #     while True:
    #         self.process_serial()

    def udp_processing_thread(self):
        while True:
            self.process_udp()

    # def serial_telem_thread(self):
    #     while True:
    #         self.serial_idle.wait()
    #         self.ser.write(self.to_be_written_to_serial + b'\n')    # endline is important for framing
    #         time.sleep(1)       # LORA UART is slow


server = RelayServer()

if __name__ == "__main__":
    # serial_processing_task = threading.Thread(target=server.serial_processing_thread)
    udp_processing_task = threading.Thread(target=server.udp_processing_thread)
    # serial_telem_task = threading.Thread(target=server.serial_telem_thread)
    # serial_telem_task.start()
    # serial_processing_task.start()
    udp_processing_task.start()
