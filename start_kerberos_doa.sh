#!/bin/bash

# Kill any previous instance
sudo pkill -f -9 start_kerberos_doa.py
sudo pkill -f -9 radio_compass.py
sudo pkill -f -9 chromium-browser

echo "Sync process starting"

# copy pre-configured settings to kerberossdr foler (save some steps in configuration in python)
cp $HOME/Desktop/kerberos_scripts/settings.json.immutable $HOME/Desktop/kerberossdr/settings.json

# start a virtual screen (kerberos need a screen to run)
sudo Xvfb :10 -ac -screen 0 800x600x8 &> /dev/null &

# start the kerberos program on virtual screen (run.sh automatically kill all previous kerberos instances)
cd $HOME/Desktop/kerberossdr && DISPLAY=:10 ./run.sh &> /dev/null &
# Wait
while ! pgrep -f hydra &> /dev/null
do 
    echo "Wait a few sec for Hydra to start..."; sleep 1;
done

# Wait a bit more
for i in {1..10}
do
    echo "Wating... $i"
    sleep 1

# Use the python enviroment
source $HOME/Desktop/kerberos_scripts/.venv/bin/activate


# Now run sync procedure, then start the compass server
cd $HOME/Desktop/kerberos_scripts && python3 -u ./kerberos_sync.py
python3 -u ./radio_compass.py &> log/radio_compass.log



