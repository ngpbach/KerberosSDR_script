#!/bin/bash
# copy pre-configured settings to kerberossdr foler (save some steps in configuration in python)
cp $HOME/Desktop/kerberos_scripts/settings.json.immutable $HOME/Desktop/kerberossdr/settings.json

# start a virtual screen (kerberos need a screen to run)
sudo Xvfb :10 -ac -screen 0 800x600x8 &

# start the kerberos program on virtual screen (run.sh automatically kill all previous kerberos instances)
cd $HOME/Desktop/kerberossdr && DISPLAY=:10 ./run.sh&

# Wait
while ! pgrep -f hydra; 
do 
    echo "Wait a few sec for Hydra to start..."; sleep 1; 
done

# Wait a bit more
sleep 10

# Use the python enviroment
source $HOME/Desktop/kerberos_scripts/.venv/bin/activate

# Kill any previous instance
pkill -f radio_compass.py

# Now run sync procedure, then start the compass server
cd $HOME/Desktop/kerberos_scripts && ./kerberos_sync.py && ./radio_compass.py&


