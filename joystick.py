#!/usr/bin/env python3

import threading
import time
import numpy as np
from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

pygame.init()

if pygame.joystick.get_count() == 0:
    raise UserWarning("No Joystick device found, ignore Joystick function")

# for i in range(pygame.joystick.get_count()):
#     js = pygame.joystick.Joystick(i)
#     print ("{} ----- ".format(i) + js.get_name())

# choice = int(input("Enter number:"))
choice = 0
js = pygame.joystick.Joystick(choice)
js.init()
print ("Using " + js.get_name())

axis_count = js.get_numaxes()
btn_count = js.get_numbuttons()
arrw_count = js.get_numhats()
axes = np.zeros(axis_count)
btns = np.zeros(btn_count)
arrws = [None]*arrw_count
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
        print("Axes value: {}".format(axes))
        print("Buttons value: {}".format(btns))
        print("Arrows value: {}".format(arrws))
        time.sleep(0.1)
