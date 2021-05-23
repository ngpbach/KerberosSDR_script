#!/bin/bash
# Kill any previous instance
sudo pkill -f relayserver.py
sudo pkill -f autohoming.py

# Use the python enviroment
cd $HOME/Desktop/kerberos_scripts
mkdir -p log
source .venv/bin/activate
# Now run the lora relay server and the control script
# Relay server need sudo to switch serial shell on/off
sudo -E python3 relayserver.py &> log/relayserver.log &
python3 autohoming.py &> log/autohoming.log &
