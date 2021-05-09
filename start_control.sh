#!/bin/bash
# Kill any previous instance
sudo pkill -f relayserver.py
sudo pkill -f autohoming.py

# Use the python enviroment
source $HOME/Desktop/kerberos_scripts/.venv/bin/activate

# Now run the lora relay server and the control script
# Relay server need sudo to switch serial shell on/off
cd $HOME/Desktop/kerberos_scripts && sudo -E ./relayserver.py &> log/relayserver.log &
cd $HOME/Desktop/kerberos_scripts && ./autohoming.py &> log/autohoming.log &
