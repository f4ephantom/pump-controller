# imports
from __future__ import print_function
import RPi.GPIO as GPIO
from datetime import datetime
import time
import sqlite3
import pandas as pd

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
FAULT_IND = 0

# State-relevant variables
PUMP_ON_TIME = None
PUMP_OFF_TIME = datetime.now()
INIT_TIME = datetime.now()
CURR_TEMP = None 

# Schedule and current value registers
SCHED = None
SCHED_LOAD_TIME = None
SCHED_MIN_OFF_TIME = None
SCHED_PUMP_ON_TIME = None
SCHED_TRIGGER_TEMP = None

# Initialize the data logging database
# if DB exists, open it
# https://docs.python.org/3/library/sqlite3.html
# if DB does not exist, create DB
# info to record in database:
# - times of state changes
# - times and values of temperature measurements

# Ensure H/W matches S/W
def push_state():
    global PIN_PUMP, PUMP_STATE, PIN_FLTI, FAULT_IND
    GPIO.output(PIN_PUMP,PUMP_STATE)
    GPIO.output(PIN_FLTI,FAULT_IND)

push_state()

# State change routines 
def pump_on():
    """Called when state change to pump_on has been triggered"""

    global PUMP_STATE, PUMP_ON_TIME
    print("pump_on() called")
    # verify that inhibit critera are not met
    if not inhibit_pump_on():

        print("pump_on state change")
        # update state variables
        PUMP_STATE = 1
        PUMP_ON_TIME = datetime.now()

        # add record to DB

        # push state to hardware
        push_state()
        
        # not sure if I need to do this yet, but will just in case
        return True

    return False


def pump_off():
    """Called when state change to pump_off has been triggered"""

    global PUMP_STATE, PUMP_OFF_TIME

    print("pump_off() called")
    # verify that inhibit critera are not met
    if not inhibit_pump_off():
        print("pump_off state change")

        # update state variables
        PUMP_STATE = 0
        PUMP_OFF_TIME = datetime.now()

        # add record to DB

        # push state to hardware
        push_state()

        # not sure if I need to do this yet, but will just in case
        return True

    return False


def inhibit_pump_on():
    """Return True if pump_on inhibit critera are satisfied"""

    global PUMP_STATE, PUMP_OFF_TIME, SCHED_MIN_OFF_TIME

    # Do not reset timer or add DB entry if pump is already on
    if PUMP_STATE == 1:
        return True

    # Do not turn on pump if it has not been off for sufficiently long
    off_time = (datetime.now() - PUMP_OFF_TIME).seconds
    if off_time < SCHED_MIN_OFF_TIME:
        return True
    
    # If we're here, no inhibit criteria are satisfied, so return False
    return False


def inhibit_pump_off():
    """Return True if pump_off inhibit critera are satisfied"""
    # At present, there are no pump_off inhibit criteria 
    return False


# Utility routines
def read_temp():
    """Read the temperature sensor"""

    global CURR_TEMP

    # query the sensor
    # since I don't have a sensor yet, let's read a temporary file
    try:
        with open('temperature.txt','r') as ifile:
            CURR_TEMP = float(ifile.readline().strip())

    except:
        CURR_TEMP = 0.0

    # add record to DB


def update_schedule():
    """Load present-time relevant values into schedule variables, 
       and reload schedule from file if time.

       This routine will be called regularly inside the main loop 
       and not queried when individual state checks are made."""

    global SCHED
    global SCHED_LOAD_TIME
    global SCHED_TRIGGER_TEMP 
    global SCHED_MIN_OFF_TIME 
    global SCHED_PUMP_ON_TIME 

    # if we need to reload the schedule from file
    reload_sched = False
    if SCHED_LOAD_TIME == None:
        reload_sched = True
    elif (datetime.now() - SCHED_LOAD_TIME).seconds > 300:
        reload_sched = True

    if reload_sched:
        SCHED = pd.read_csv('schedule.txt',delim_whitespace=True)
        SCHED_LOAD_TIME = datetime.now()
        SCHED['start_time'] = pd.to_datetime(SCHED['start_time'].str.strip(),
                                             format='%H:%M:%S')
        SCHED['end_time'] = pd.to_datetime(SCHED['end_time'].str.strip(),
                                             format='%H:%M:%S')

    # find row of schedule relevent to current time
    a = datetime.now().time()
    mask = SCHED.apply(lambda row: True if row['start_time'].time() < a and 
                               row['end_time'].time() >= a else False,axis=1)
    select = SCHED[mask]
    # I should probably check to make sure this returns only one valid entry

    SCHED_TRIGGER_TEMP = select['set_temp'].iloc[0]
    SCHED_MIN_OFF_TIME = select['min_off_time'].iloc[0]
    SCHED_PUMP_ON_TIME = select['on_time'].iloc[0]


def debug_print_state():
    global PUMP_STATE, FAULT_IND
    global PUMP_ON_TIME, PUMP_OFF_TIME, INIT_TIME, CURR_TEMP
    global SCHED_LOAD_TIME, SCHED_MIN_OFF_TIME, SCHED_PUMP_ON_TIME
    global SCHED_TRIGGER_TEMP

    print("\nState Variables:")
    print("  PUMP_STATE: {:}".format(PUMP_STATE))
    print("  FAULT_IND: {:}".format(FAULT_IND))
    print("\nState-relevant Variables:")
    print("  PUMP_ON_TIME: {:}".format(PUMP_ON_TIME))
    print("  PUMP_OFF_TIME: {:}".format(PUMP_OFF_TIME))
    print("  INIT_TIME: {:}".format(INIT_TIME))
    print("  CURR_TEMP: {:}".format(CURR_TEMP))
    print("\nSchedule Variables:")
    print("  SCHED_LOAD_TIME: {:}".format(SCHED_LOAD_TIME))
    print("  SCHED_MIN_OFF_TIME: {:}".format(SCHED_MIN_OFF_TIME))
    print("  SCHED_PUMP_ON_TIME: {:}".format(SCHED_PUMP_ON_TIME))
    print("  SCHED_TRIGGER_TEMP: {:}".format(SCHED_TRIGGER_TEMP))
  

# Iterrupt callback function
def override_callback(channel):
    """Trigger a pump_on state change request when button pressed"""
    pump_on()

# register the interrupt pin and callback function
GPIO.add_event_detect(PIN_OVRR, GPIO.FALLING, callback=override_callback, 
                      bouncetime=300)

# Main loopmas = SCHED.apply(lambda row: True if row['start_time'].time() < a and row['end_time'].time() >= a else False,axis=1)
try:
    print("Initialization Complete.  Beginning loop.")
    while True:
        update_schedule()
        read_temp()

        debug_print_state()

        if CURR_TEMP < SCHED_TRIGGER_TEMP:
            pump_on()

        if PUMP_STATE == 1:
            ontime = (datetime.now() - PUMP_ON_TIME).seconds
            if ontime > SCHED_PUMP_ON_TIME:
                pump_off()

        # sleep for 30s
        time.sleep(5) 

except KeyboardInterrupt:
    pass

print('Exiting on keyboard iterrupt')
