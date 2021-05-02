#!/bin/bash
cp settings.json.immutable $HOME/Desktop/kerberossdr/settings.json
sudo Xvfb :10 -ac -screen 0 800x600x8 &
cd $HOME/Desktop/kerberossdr && DISPLAY=:10 ./run.sh&
while ! pgrep -f hydra; 
do 
    echo "wait a few sec for Hydra to start..."; sleep 1; 
done 
sleep 5
source $HOME/Desktop/kerberossdr/.venv/bin/activate
cd $HOME/Desktop/kerberos_scripts && DISPLAY=:10 python3 kerberos_sync.py &&  python3 radio_compass.py


