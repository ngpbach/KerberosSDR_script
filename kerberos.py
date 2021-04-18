#!/usr/bin/python3
import os
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options
import json
import time

SERVERIP = '192.168.0.10'
FREQ = 121.65


options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(10)

""" Init page: disable DC compensation and FIR filter, and start processing """
driver.get("http://" + SERVERIP + ":8080/init")
config_set_btn = driver.find_element_by_css_selector("input[value='Update Receiver Paramaters']")
config_set_btn.click()

dc_comp = driver.find_element_by_css_selector("input[name='dc_comp']")
if (dc_comp.is_selected()):
    dc_comp.click()

fir_size = driver.find_element_by_css_selector("input[name='fir_size']")
fir_size.clear()
fir_size.send_keys('0')

iq_set_btn = driver.find_element_by_css_selector("input[value='Update IQ Paramaters']")
iq_set_btn.click()

start_btn = driver.find_element_by_css_selector("input[value='Start Processing']")
start_btn.click()

""" Sync page: enable noise source and do sample sync and IQ calibration, then disable noise source """
driver.get("http://" + SERVERIP + ":8080/sync")
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

""" Init page: enable DC comp and filter again """
# driver.get("http://" + SERVERIP + ":8080/init")

# dc_comp = driver.find_element_by_css_selector("input[name='dc_comp']")
# if (not dc_comp.is_selected()):
#     dc_comp.click()

# fir_size = driver.find_element_by_css_selector("input[name='fir_size']")
# fir_size.clear()
# fir_size.send_keys('100')

# iq_set_btn = driver.find_element_by_css_selector("input[value='Update IQ Paramaters']")
# iq_set_btn.click()

""" DOA page: enable DOA """
# driver.get("http://" + SERVERIP + ":8080/doa")

# doa = driver.find_element_by_css_selector("input[name='en_doa']")
# if (not doa.is_selected()):
#     doa.click()

# update = driver.find_element_by_css_selector("input[value='Update DOA']")
# update.click()


# driver.get("http://192.168.0.10:8081/compass.html")
# WebDriverWait(driver, 1000)
# doa = driver.find_elements_by_id("doa")
# while(True):
#     print(doa[0].text)
#     time.sleep(1)

