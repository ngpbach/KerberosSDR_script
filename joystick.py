#!/usr/bin/env python3

import time
import sys
import numpy as np
import serial
import json
from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import logging as log
log.basicConfig(format='[%(levelname)s][%(asctime)s]%(message)s', level=log.DEBUG)

pygame.init()
if pygame.joystick.get_count() == 0:
    raise RuntimeError("No Joystick device found, Joystick function unavailable")

choice = 0
if __name__ == "__main__":
    for i in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(i)
        print ("{} ----- ".format(i) + js.get_name())

    choice = int(input("Enter number:"))

js = pygame.joystick.Joystick(choice)
js.init()
log.info("Using " + js.get_name())

axis_count = js.get_numaxes()
btn_count = js.get_numbuttons()
arrw_count = js.get_numhats()
axes = [0]*axis_count
btns = [0]*btn_count
arrws = [0]*arrw_count
deadband = 0.05

def joystick_update():
    pygame.event.pump()
    for i in range (axis_count):
        axes[i] = js.get_axis(i)
        if abs(axes[i]) < deadband:
            axes[i] = 0
    for i in range (btn_count):
        btns[i] = js.get_button(i)
    for i in range (arrw_count):
        arrws[i] = js.get_hat(i)

if __name__ == "__main__":
    while(1):
        joystick_update()
        log.debug("\n\tAxes value: {}\n\tButtons value: {}\n\tArrows value: {}".format(axes, btns, arrws))
        time.sleep(0.1)
