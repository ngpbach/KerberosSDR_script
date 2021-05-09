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

#TODO: switch pi serial to normal UART when script start

cmd_start_console = 'sudo stty -F /dev/serial0 9600 && sudo systemctl start serial-getty@serial0.service'            # start the serial console when this program exit
cmd_stop_console = 'sudo systemctl stop serial-getty@serial0.service'            # stop the serial console when this program start
cmd_start_kerberos = '/home/pi/Desktop/kerberos_scripts/start_kerberos_doa.sh'      # start the kerberos syncing procedure and then start DOA server

subprocess.run(cmd_stop_console, shell=True)
log.info("Relay server started. Serial console mode disable")

def terminate():
    subprocess.run(cmd_start_console, shell=True)
    log.info("Relay server exiting. Serial console mode enable")

atexit.register(terminate)

WHOAMI = "pi"
TARGET = "gcs"
PORT_RELAY = 5000      # netcat link all serial stream to localhost on this UDP port
PORT_KERB = 5001
PORT_JS = 5002
LOCALHOST = "127.0.0.1"

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
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_RELAY):
        self.idle = threading.Event()       # the LORA module corrupt message a lot if sending & receiving at the same time. Use Event to cease sending telem if start receiving command, and start sending telem once no longer receiving command
        try:
            self.ser = serial.Serial(DEVICE, BAUD, timeout=1)
            time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
            self.ser.reset_input_buffer()
        except serial.SerialException as msg:
            log.error(msg)
            raise
        
        self.sock = socket.socket(socket.AF_INET,   # Internet
                                socket.SOCK_DGRAM)  # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(0.1)
    
    def serial_to_udp(self):
        try:
            message = self.ser.readline()
            if not message:
                self.idle.set()
                log.debug("Idle: Serial read timeout")
                return

            else:
                self.idle.clear()

            log.debug(message)
            packet = json.loads(message.decode())

            if packet["type"] == "js":
                    self.sock.sendto(message, (LOCALHOST, PORT_JS))
                
            elif packet["type"] == "cmd":
                if packet["cmd"] == "sync":
                    packet["type"] = "ack"
                    packet["cmd"] = "sync"
                    message = (json.dumps(packet) + '\n')
                    self.ser.write(message.encode())    # endline is important for framing
                    process = Popen(cmd_start_kerberos, preexec_fn=demote(1000), stdout=PIPE, stderr=PIPE, bufsize=1)

                    for line in process.stdout:
                        self.ser.write(line)
                        log.info(line.decode())
                        if "done" in line.decode():
                            break

                    time.sleep(1)


                if packet["cmd"] == "exit":
                    packet["type"] = "ack"
                    packet["cmd"] = "exit"
                    message = (json.dumps(packet) + '\n')
                    self.ser.write(message.encode())    # endline is important for framing
                    time.sleep(1)
                    exit(0)
                
                self.ser.reset_input_buffer()

        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)
        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)

    def udp_to_serial(self):
        self.idle.wait()
        try:
            message = None
            # Empty old packets in buffer
            while True:
                try:
                    message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
                except:
                    break
            
            if message:
                log.debug(message)
                packet = json.loads(message.decode())

                if packet["type"] == "telem":
                    self.ser.write(message + b'\n')    # endline is important for framing

        except UnicodeDecodeError:
            log.error("Gargabe characters received: %s", message)
        except json.JSONDecodeError:
            log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)
        except KeyError as msg:
            log.error("Packet received has no [%s] key", msg)


server = RelayServer()

def serial_to_udp_thread():
    while True:
        server.serial_to_udp()

def udp_to_serial_thread():
    while True:
        server.udp_to_serial()
        time.sleep(1)   # wireless serial is slow


if __name__ == "__main__":
    serial_to_udp = threading.Thread(target=serial_to_udp_thread)
    udp_to_serial = threading.Thread(target=udp_to_serial_thread, daemon = True)
    serial_to_udp.start()
    udp_to_serial.start()
