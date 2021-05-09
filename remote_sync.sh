#!/bin/bash

stty -F /dev//dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0 9600

echo "This script will trigger the Kerberos Calibration process by sending a command to companion Pi over LORA serial"
echo "{\"type\":\"cmd\",\"cmd\":\"sync\"}" > /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0
echo "Sync command sent. You should see a line {\"type\": \"ack\", \"cmd\": \"sync\"} as the respond. If not, please quit and start over"
echo "Simply Ctrl-C to exit after sync is done"

cat < /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0LNG4V-if00-port0