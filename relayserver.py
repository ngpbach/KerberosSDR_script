#!/usr/bin/env python3
"""
Create redirection from serial port to UDP
Act as relay server for the pi to compile and sort serial packet and send through UDP to the appropriate port
Swith to Pi serial console mode when commanded to
"""
import time
import socket
import serial
import json
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.DEBUG)

#TODO: switch pi serial to normal UART when script start


""" Device specific settings """
# BAUD = 9600    # baud of LORA UART
# DEVICE = "/dev/serial0"
# try:
#     ser = serial.Serial(DEVICE, BAUD)
#     time.sleep(1)   # a bug in pyserial requires to wait a little before it can be used (or flush)
#     ser.reset_input_buffer()
# except serial.SerialException as msg:
#     log.error(msg)

# def terminate():
#     ser.close()
#     log.info("Serial closed")

WHOAMI = "pi"
TARGET = "gcs"
PORT_SERIAL = 5000      # netcat link all serial stream to localhost on this UDP port
PORT_KERB = 5005
PORT_JS = 5006
LOCALHOST = "127.0.0.1"

class RelayServer:
    """ Convenient class for forwarding JSON packet to the appropriate port """
    def __init__(self, UDP_IP = LOCALHOST, UDP_PORT = PORT_SERIAL):
        self.sock = socket.socket(socket.AF_INET,   # Internet
                                socket.SOCK_DGRAM)  # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.settimeout(1)
    
    def update(self):
        while True:
            try:
                message, addr = self.sock.recvfrom(1024) # buffer size is 1024 bytes
                log.debug(message)                
                packet = json.loads(message.decode())

                if packet["target"] == WHOAMI:
                    if packet["type"] == "js":
                        self.sock.sendto(message, (LOCALHOST, PORT_JS))
                    
                    elif packet["type"] == "cmd":
                        if packet["action"] == "to_serial_console":
                            # TODO: switch pi to serial console mode and exit
                            pass

                
            except socket.timeout:
                log.debug("Socket timed out waiting for msg")
            except json.JSONDecodeError:
                log.error("Corrupt or incorrect format\n\tReceived msg: %s", message.decode())
            except KeyError as msg:
                log.error("Packet received has no [%s] key", msg)

server = RelayServer()

if __name__ == "__main__":
    while (True):
        server.update()
        time.sleep(0.001)