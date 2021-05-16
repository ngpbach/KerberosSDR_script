#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options
import time
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.INFO)

SERVERIP = '127.0.0.1'

print("Make sure that either the radio band of interest is completely silent (no beacons or radio station broadcasting), or all kerberos antenna are disconnected from the board, in order to perform sync process correctly")
print("Going through kerberos settings and syncing sequence, will take about 30 secs. Be patient...")

options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)
max_tries = 10
""" Init page: disable DC compensation and FIR filter, and start processing """
for i in range(max_tries):     # try 10 times   
    try:
        driver.get("http://" + SERVERIP + ":8080/init")
        break
    except ec.WebDriverException as msg:
        if i == max_tries-1:
            raise
        log.debug(msg)
        time.sleep(1)
    
print("Use Firefox to access\nhttp://192.168.43.10:8080/sync\nto visually confirm the syncing process.")

config_set_btn = driver.find_element_by_css_selector("input[value='Update Receiver Paramaters']")
config_set_btn.click()
time.sleep(1)

dc_comp = driver.find_element_by_css_selector("input[name='dc_comp']")
if (dc_comp.is_selected()):
    dc_comp.click()

fir_size = driver.find_element_by_css_selector("input[name='fir_size']")
fir_size.clear()
fir_size.send_keys('0')

iq_set_btn = driver.find_element_by_css_selector("input[value='Update IQ Paramaters']")
iq_set_btn.click()
time.sleep(1)

start_btn = driver.find_element_by_css_selector("input[value='Start Processing']")
start_btn.click()
time.sleep(1)

""" Sync page: enable noise source and do sample sync and IQ calibration, then disable noise source """
for i in range(max_tries):     # try 10 times
    try:    
        driver.get("http://" + SERVERIP + ":8080/sync")
        break
    except ec.webdriverException as msg:
        if i == max_tries-1:
            raise
        log.debug(msg)
        time.sleep(1)

# check_sync_btn = driver.find_element_by_css_selector("input[value='Enable Noise Source & Sync Display']")
# check_sync_btn.click()

sync  = driver.find_element_by_css_selector("input[name='en_sync']")
if (not sync.is_selected()):
    sync.click()

noise = driver.find_element_by_css_selector("input[name='en_noise']")
if (not noise.is_selected()):
    noise.click()

update = driver.find_element_by_css_selector("input[value='Update']")
update.click()
time.sleep(1)

sync_btn = driver.find_element_by_css_selector("input[value='Sample Sync']")
sync_btn.click()
for i in range(5):
    print("Wait some time for sample sync:" + str(5-i))
    time.sleep(1)

cal_btn = driver.find_element_by_css_selector("input[value='Calibrate IQ']")
cal_btn.click()
for i in range(5):
    print("Wait some time for IQ calibration:" + str(5-i))
    time.sleep(1)

# uncheck_sync_btn = driver.find_element_by_css_selector("input[value='Disable Noise Source & Sync Display']")
# uncheck_sync_btn.click()

sync  = driver.find_element_by_css_selector("input[name='en_sync']")
if (sync.is_selected()):
    sync.click()

noise = driver.find_element_by_css_selector("input[name='en_noise']")
if (noise.is_selected()):
    noise.click()

update = driver.find_element_by_css_selector("input[value='Update']")
update.click()
time.sleep(1)

""" Init page: enable DC comp and filter again """
for i in range(max_tries):     # try 10 times
    try:
        driver.get("http://" + SERVERIP + ":8080/init")
        break
    except ec.webdriverException as msg:
        if i == max_tries-1:
            raise
        log.debug(msg)
        time.sleep(1)

dc_comp = driver.find_element_by_css_selector("input[name='dc_comp']")
if (not dc_comp.is_selected()):
    dc_comp.click()

fir_size = driver.find_element_by_css_selector("input[name='fir_size']")
fir_size.clear()
fir_size.send_keys('100')

iq_set_btn = driver.find_element_by_css_selector("input[value='Update IQ Paramaters']")
iq_set_btn.click()
time.sleep(1)

""" DOA page: enable DOA """
for i in range(10):     # try 10 times
    try:
        driver.get("http://" + SERVERIP + ":8080/doa")
        break
    except ec.webdriverException as msg:
        if i == 9:
            raise
        log.debug(msg)
        time.sleep(1)

doa = driver.find_element_by_css_selector("input[name='en_doa']")
if (not doa.is_selected()):
    doa.click()

update = driver.find_element_by_css_selector("input[value='Update DOA']")
update.click()
time.sleep(1)


driver.quit()
print("Sync process done")

exit(0)
