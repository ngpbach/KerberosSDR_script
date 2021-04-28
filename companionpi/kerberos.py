#!/usr/bin/env python3
import os
import re
import socket
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s] %(message)s', level=log.DEBUG)
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options
import json
import time


# SERVERIP = '192.168.0.10'

# print("Make sure that either the radio band of interest is completely silent (no beacons or radio station broadcasting), or all kerberos antenna are disconnected from the board, in order to perform sync process correctly")
# input("Press Enter to continue...")
# print("Going through kerberos settings and syncing sequence, will take about 30 secs. Be patient...")

# options = Options()
# options.headless = True
# driver = webdriver.Chrome(options=options)
# driver.implicitly_wait(30)

# """ Init page: disable DC compensation and FIR filter, and start processing """
# driver.get("http://" + SERVERIP + ":8080/init")
# config_set_btn = driver.find_element_by_css_selector("input[value='Update Receiver Paramaters']")
# config_set_btn.click()

# dc_comp = driver.find_element_by_css_selector("input[name='dc_comp']")
# if (dc_comp.is_selected()):
#     dc_comp.click()

# fir_size = driver.find_element_by_css_selector("input[name='fir_size']")
# fir_size.clear()
# fir_size.send_keys('0')

# iq_set_btn = driver.find_element_by_css_selector("input[value='Update IQ Paramaters']")
# iq_set_btn.click()

# start_btn = driver.find_element_by_css_selector("input[value='Start Processing']")
# start_btn.click()

# """ Sync page: enable noise source and do sample sync and IQ calibration, then disable noise source """
# driver.get("http://" + SERVERIP + ":8080/sync")

# # check_sync_btn = driver.find_element_by_css_selector("input[value='Enable Noise Source & Sync Display']")
# # check_sync_btn.click()

# sync  = driver.find_element_by_css_selector("input[name='en_sync']")
# if (not sync.is_selected()):
#     sync.click()

# noise = driver.find_element_by_css_selector("input[name='en_noise']")
# if (not noise.is_selected()):
#     noise.click()

# update = driver.find_element_by_css_selector("input[value='Update']")
# update.click()

# sync_btn = driver.find_element_by_css_selector("input[value='Sample Sync']")
# sync_btn.click()
# for i in range(5):
#     print("Wait some time for sample sync:" + str(5-i))
#     time.sleep(1)

# cal_btn = driver.find_element_by_css_selector("input[value='Calibrate IQ']")
# cal_btn.click()
# for i in range(5):
#     print("Wait some time for IQ calibration:" + str(5-i))
#     time.sleep(1)

# # uncheck_sync_btn = driver.find_element_by_css_selector("input[value='Disable Noise Source & Sync Display']")
# # uncheck_sync_btn.click()

# sync  = driver.find_element_by_css_selector("input[name='en_sync']")
# if (sync.is_selected()):
#     sync.click()

# noise = driver.find_element_by_css_selector("input[name='en_noise']")
# if (noise.is_selected()):
#     noise.click()

# update = driver.find_element_by_css_selector("input[value='Update']")
# update.click()

# """ Init page: enable DC comp and filter again """
# driver.get("http://" + SERVERIP + ":8080/init")

# dc_comp = driver.find_element_by_css_selector("input[name='dc_comp']")
# if (not dc_comp.is_selected()):
#     dc_comp.click()

# fir_size = driver.find_element_by_css_selector("input[name='fir_size']")
# fir_size.clear()
# fir_size.send_keys('100')

# iq_set_btn = driver.find_element_by_css_selector("input[value='Update IQ Paramaters']")
# iq_set_btn.click()

# """ DOA page: enable DOA """
# driver.get("http://" + SERVERIP + ":8080/doa")

# doa = driver.find_element_by_css_selector("input[name='en_doa']")
# if (not doa.is_selected()):
#     doa.click()

# update = driver.find_element_by_css_selector("input[value='Update DOA']")
# update.click()

# """ Compass page: get the bearing info """
# driver.get("http://192.168.0.10:8081/compass.html?MIN_PWR=10&MIN_CONF=3")
# doa = driver.find_element_by_id("doa")

# def bearing_update():
#     bearing = int(re.findall(r'\d+', doa.text)[0])
#     return bearing


if __name__ == "__main__":
    UDP_IP = "127.0.0.1"
    UDP_PORT = 5005
    log.info("Sending radio compass value through UDP...")
    log.info("UDP target IP: %s", UDP_IP)
    log.info("UDP target port: %s", UDP_PORT)
    sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP

    while(True):
        # compass = int(re.findall(r'\d+', doa.text)[0]) - 45
        compass = int("40")
        message = json.dumps({"bearing":compass}, separators=(',', ':'))
        log.info(message)
        sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
        time.sleep(1)

