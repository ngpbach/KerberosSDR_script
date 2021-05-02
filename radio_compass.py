#!/usr/bin/env python3
import os
import re
import socket
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options
import json
import time
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s][%(funcName)s]%(message)s', level=log.DEBUG)


SERVERIP = '127.0.0.1'

options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(30)

# """ Compass page: get the bearing info """
# driver.get("http://" + SERVERIP + ":8081/compass")
# doa = driver.find_element_by_id("doa")

UDP_IP = "127.0.0.1"
UDP_PORT = 5001
print("Sending bearing value through UDP...")
print("UDP target IP: %s" % UDP_IP)
print("UDP target port: %s" % UDP_PORT)
sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
packet = {}

while(True):
    # bearing = re.findall(r'\d+', doa.text)[0]
    packet['bearing'] = 100
    packet['strength'] = 10
    packet['confidence'] = 5
    message = json.dumps(packet)
    log.debug(message)           
    sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
    time.sleep(1)

