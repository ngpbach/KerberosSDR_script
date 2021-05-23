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
BEARING_OFFSET = 45

options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)

""" Compass page: get the bearing info """
max_tries = 10
""" Init page: disable DC compensation and FIR filter, and start processing """
for i in range(max_tries):     # try 10 times
    try:
        driver.get("http://" + SERVERIP + ":8081/compass.html")
        break
    except ec.webdriverException as msg:
        if i == max_tries-1:
            raise
        log.debug(msg)
        time.sleep(1)

doa = driver.find_element_by_id("doa")
pwr = driver.find_element_by_id("pwr")
conf = driver.find_element_by_id("conf")

UDP_IP = "127.0.0.1"
UDP_PORT = 5001
print("Sending bearing value through UDP...")
print("UDP target IP: %s" % UDP_IP)
print("UDP target port: %s" % UDP_PORT)
sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
packet = {}
print("Radio compass started")

while(True):
    bearing = re.findall(r'\d+', doa.text)[0]
    power = re.findall(r'\d+', pwr.text)[0]
    confidence = re.findall(r'\d+', conf.text)[0]
    packet['bearing'] = int(bearing) - BEARING_OFFSET
    packet['power'] = int(power)
    packet['confidence'] = int(confidence)
    message = json.dumps(packet)
    log.debug(message)
    sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
    time.sleep(1)

