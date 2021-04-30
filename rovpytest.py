from rovpy import rovpy
import time
rovpy.connectrov("STABILIZE","/dev/serial/by-id/usb-ArduPilot_Pixhawk1_25004E000651383034343237-if00")
rovpy.arm()

time.sleep(10)

rovpy.disarm()