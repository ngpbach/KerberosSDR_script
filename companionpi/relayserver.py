#!/usr/bin/env python3
"""
Act as relay server for the pi to compile and sort serial packet and send through UDP to the appropriate port, and vice versa
Swith to Pi serial console mode when commanded to
"""
import time
import threading
import socket
import serial
import json
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.INFO)

#TODO: switch pi serial to normal UART when script start

WHOAMI = "pi"
TARGET = "gcs"
PORT_RELAY = 5000      # netcat link all serial stream to localhost on this UDP port
PORT_KERB = 5001
PORT_JS = 5002
LOCALHOST = "127.0.0.1"

""" Device specific settings """
BAUD = 9600    # baud of LORA UART
DEVICE = "/dev/serial0"
# DEVICE = "./pttyout"

class RelayServer:
    """ Convenient class for forwarding JSON packet to the appropriate port """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_RELAY):
        try:
            self.ser = serial.Serial(DEVICE, BAUD, timeout=5)
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
               log.error("Serial read timeout")
               return

           #log.debug(message)                
           packet = json.loads(message.decode())

           if packet["type"] == "js":
               self.sock.sendto(message, (LOCALHOST, PORT_JS))
               
           elif packet["type"] == "cmd":
               if packet["act"] == "console":
                   # TODO: switch pi to serial console mode and exit
                   pass

           
       except socket.timeout:
           log.debug("Socket timed out waiting for msg")
       except json.JSONDecodeError:
           log.error("Corrupt or incorrect format\n\tReceived msg: %s", message)
       except KeyError as msg:
           log.error("Packet received has no [%s] key", msg)

    def udp_to_serial(self):
       try:
           message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
           # log.debug(message)                
           packet = json.loads(message.decode())

           if packet["type"] == "telem":
               self.ser.write(message + b'\n')    # endline is important for framing
                               
       except socket.timeout:
           log.debug("Socket timed out waiting for msg")
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
    udp_to_serial = threading.Thread(target=udp_to_serial_thread)
    serial_to_udp.start()
    udp_to_serial.start()
