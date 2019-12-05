# imports
import RPi.GPIO as GPIO
from datetime import datetime
import time
import sqlite3

# set GPIO pin numbering scheme
GPIO.setmode(GPIO.BCM)

# setup pin directions
PIN_PUMP = 17 # Relay control (BCM 17, board 11)
PIN_OVRR = 27 # Override switch (BCM 27, board 13)
PIN_TEMP =  4 # Temperature sensor data (BCM 4, board 7)
PIN_FLTI = 23 # Fault LED (BCM 23, board 16)

GPIO.setup(PIN_PUMP, GPIO.OUT)
GPIO.setup(PIN_OVRR, GPIO.IN)
#GPIO.setup(PIN_TEMP, GPIO.IN) # not sure yet how to interface with this
GPIO.setup(PIN_FLTI, GPIO.OUT)

# Temperature sensor (Uses one-wire protocol...tutorial suggests BCM 4)
# https://pinout.xyz/pinout/1_wire#
# https://thepihut.com/blogs/raspberry-pi-tutorials/18095732-sensors-temperature-with-the-1-wire-interface-and-the-ds18b20

# State variables
PUMP_STATE = 0
PUMP_ON_TIME = None
PUMP_OFF_TIME = datetime.now()
INIT_TIME = datetime.now()
FAULT_IND = 0
CURR_TEMP = None 

# Initialize the state database
# if DB exists, open it
# https://docs.python.org/3/library/sqlite3.html
# if DB does not exist, create DB


# Ensure H/W matches S/W
def set_hw():
    GPIO.out(PIN_PUMP,PUMP_STATE)
    GPIO.out(PIN_FLTI,FAULT_IND)

set_hw()

# Routines
def pump_on():
    PUMP_STATE = 1
    PUMP_ON_TIME = datetime.now()
    # add record to DB
    set_hw()

def pump_off():
    PUMP_STATE = 0
    PUMP_OFF_TIME = datetime.now()
    # add record to DB
    set_hw()

def read_temp():
    # add record to DB
    pass

def load_schedule():
    # this should be called periodically in case it changes
    pass


def check_schedule():
    # check to see if the current temperature trips the pump per the schedule
    # return whether or not to turn on the pump
    pass

# Iterrupt callback function
def override_callback(channel):
    if PUMP_STATE == 0:
        pump_on()

GPIO.add_event_detect(PIN_OVRR, GPIO.FALLING, callback=override_callback, 
                      bouncetime=300)

# Main loop
try:
    while True:
        # Check the temperature

        # Check schedule

        # if necessary, turn on the pump

        # if necessary, turn off the pump

        # sleep for 30s
        time.sleep(30)

except KeyboardInterrupt:
    pass

print('Exiting on keyboard iterrupt')
