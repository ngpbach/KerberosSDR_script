#!/bin/bash

cp settings.json.immutable $HOME/Desktop/kerberossdr/settings.json
sudo Xvfb :10 -ac -screen 0 800x600x8 &
cd $HOME/Desktop/kerberossdr && DISPLAY=:10 ./run.sh&
while ! pgrep -f hydra; 
do 
    echo "wait a few sec for Hydra to start..."; sleep 1; 
done 
sleep 5
cd $HOME/Desktop/kerberos_scripts && DISPLAY=:10 ./kerberos.py

