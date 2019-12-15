# imports
from __future__ import print_function
import RPi.GPIO as GPIO
from datetime import datetime
import time
import sqlite3
import pandas as pd
import glob

# set GPIO pin numbering scheme
GPIO.setmode(GPIO.BCM)

# setup pin directions
PIN_PUMP = 16 # Relay control (BCM 17, board 11)
PIN_OVRR = 27 # Override switch (BCM 27, board 13)
#PIN_TEMP =  4 # Temperature sensor data (BCM 4, board 7)
PIN_FLTI = 23 # Fault LED (BCM 23, board 16)

GPIO.setup(PIN_PUMP, GPIO.OUT)
GPIO.setup(PIN_OVRR, GPIO.IN)
#GPIO.setup(PIN_TEMP, GPIO.IN) # not sure yet how to interface with this
GPIO.setup(PIN_FLTI, GPIO.OUT)

# Temperature sensor (BCM 4)
# I'm using the information here for the DS18B20 temperature sensor:
#   https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/software
#
# this SO page had an interesting comment about the file read operation triggering a conversion, so 750ms are needed between open and read in order to get a 'current' temperature
#   https://raspberrypi.stackexchange.com/questions/75167/ds18b20-w1-slave-file-stamp-doesnt-change
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
DEVICE_FILE = device_folder + '/w1_slave'

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
DB_CONN = sqlite3.connect('database.sq3')
DB_CUR = DB_CONN.cursor()

# if DB has not been initialized, prepare it for use
DB_CUR.execute("""
SELECT count(name) 
FROM sqlite_master 
WHERE type='table' AND name='sensors'""")
if DB_CUR.fetchone()[0] != 1:
    DB_CUR = DB_CONN.executescript(open('schema.sql','r').read())

    # populate sensor table
    DB_CUR.execute('insert into sensors (id,description) '\
                   'values (1,"pipe sensor 1")')
    DB_CUR.execute('insert into sensors (id,description) '\
                   'values (2,"board sensor")')
    
    # populate state table
    DB_CUR.execute('insert into states (id,description) '\
                   'values (1,"pump off")')
    DB_CUR.execute('insert into states (id,description) '\
                   'values (2,"pump on")')
    DB_CUR.execute('insert into states (id,description) '\
                   'values (3,"fault off")')
    DB_CUR.execute('insert into states (id,description) '\
                   'values (4,"fault on")')
    
    # populate trigger table
    DB_CUR.execute('insert into triggers (id,description) '\
                   'values (1,"temperature")')
    DB_CUR.execute('insert into triggers (id,description) '\
                   'values (2,"override")')
    DB_CUR.execute('insert into triggers (id,description) '\
                   'values (3,"timeout")')
    DB_CUR.execute('insert into triggers (id,description) '\
                   'values (4,"init")')

    DB_CONN.commit()

# Ensure H/W matches S/W
def push_state():
    global PIN_PUMP, PUMP_STATE, PIN_FLTI, FAULT_IND
    GPIO.output(PIN_PUMP,PUMP_STATE)
    GPIO.output(PIN_FLTI,FAULT_IND)

# State change routines 
def pump_on(trigger):
    """Called when state change to pump_on has been triggered"""

    global PUMP_STATE, PUMP_ON_TIME,DB_CUR,DB_CONN
    print("pump_on() called")
    # verify that inhibit critera are not met
    if not inhibit_pump_on():

        print("pump_on state change")
        # update state variables
        PUMP_STATE = 1
        PUMP_ON_TIME = datetime.now()

        # add record to DB
        # Is not working when called from interrupt because the process is 
        # different and a new sqlite connection object is needed
        try:
            DB_CUR.execute('INSERT INTO statechanges (time,'\
              'new_state,cause) values (?,?,?)',(datetime.now(),2,trigger))
            DB_CONN.commit()
        except:
            print("ERROR: Failed to add entry to database")

        # push state to hardware
        push_state()
        
        # not sure if I need to do this yet, but will just in case
        return True

    return False


def pump_off(trigger):
    """Called when state change to pump_off has been triggered"""

    global PUMP_STATE, PUMP_OFF_TIME, DB_CUR, DB_CONN

    print("pump_off() called")
    # verify that inhibit critera are not met
    if not inhibit_pump_off():
        print("pump_off state change")

        # update state variables
        PUMP_STATE = 0
        PUMP_OFF_TIME = datetime.now()

        # add record to DB
        try:
            DB_CUR.execute('INSERT INTO statechanges (time,'\
              'new_state,cause) values (?,?,?)',(datetime.now(),1,trigger))
            DB_CONN.commit()
        except:
            print("ERROR: Failed to add entry to database")

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


def fault_on(trigger):
    """Set the falut indicator LED"""

    # Set the state indicator
    FAULT_IND = 1

    # add record to DB
    try:
        DB_CUR.execute('INSERT INTO statechanges (time,'\
          'new_state,cause) values (?,?,?)',(datetime.now(),4,trigger))
        DB_CONN.commit()
    except:
        print("ERROR: Failed to add entry to database")

    # push to hardware
    push_state() 


def fault_off(trigger):
    """Clear the falut indicator LED"""

    # Set the state indicator
    FAULT_IND = 0

    # add record to DB
    try:
        DB_CUR.execute('INSERT INTO statechanges (time,'\
          'new_state,cause) values (?,?,?)',(datetime.now(),3,trigger))
        DB_CONN.commit()
    except:
        print("ERROR: Failed to add entry to database")

    # push to hardware
    push_state() 


def inhibit_pump_off():
    """Return True if pump_off inhibit critera are satisfied"""
    # At present, there are no pump_off inhibit criteria 
    return False


# Utility routines
def read_temp():
    """Read the temperature sensor"""

    global CURR_TEMP, DB_CUR, DB_CONN, DEVICE_FILE, FAULT_IND

    # query the sensor
    try:
        # since I don't have a sensor yet, let's read a temporary file
        #with open('temperature.txt','r') as ifile:
        #    CURR_TEMP = float(ifile.readline().strip())

        with open(DEVICE_FILE,'r') as ifile:
            time.sleep(1.00) # only needs to be 750 ms, but allow some slop
            lines = ifile.readlines()

        if lines[0].strip()[-3:] == 'YES':
            equals_pos = lines[1].find('t=')
            if equals_pos != -1:
                temp_string = lines[1][equals_pos+2:]
                temp_c = float(temp_string) / 1000.0
                CURR_TEMP = temp_c * 9.0 / 5.0 + 32.0 
                
            else:
                print("ERROR reading temperature.  Cannot find t=")
                print(lines)
                raise ValueError
        else:
            print("ERROR reading temperature.  Cannot find YES")
            print(lines)
            raise ValueError
            
    except:
        # If there's an error, set temperature high enough to shut off pump
        # and set the fault indicator
        print("ERROR reading temperature.  Cannot open file.")
        CURR_TEMP = 200.0
        fault_on(1)

    else:
        # check to see if we should clear fault light
        if FAULT_IND == 1:
            fault_off(1)

    # add record to DB
    try:
        DB_CUR.execute('INSERT INTO measurements (sensor_id,time,value) '\
          'values (?,?,?)',(1,datetime.now(),CURR_TEMP))
        DB_CONN.commit()
    except:
        print("ERROR: Failed to add entry to database")


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
    pump_on(2)

# register the interrupt pin and callback function
GPIO.add_event_detect(PIN_OVRR, GPIO.FALLING, callback=override_callback, 
                      bouncetime=300)

# Main loopmas = SCHED.apply(lambda row: True if row['start_time'].time() < a and row['end_time'].time() >= a else False,axis=1)
try:
    # set state to pump_off after initialization
    pump_off(4)
    fault_off(4)
    print("Initialization Complete.  Beginning loop.")

    while True:
        update_schedule()
        read_temp()

        debug_print_state()

        if CURR_TEMP < SCHED_TRIGGER_TEMP:
            pump_on(1)

        if PUMP_STATE == 1:
            ontime = (datetime.now() - PUMP_ON_TIME).seconds
            if ontime > SCHED_PUMP_ON_TIME:
                pump_off(3)

        # sleep for 30s
        time.sleep(5) 

except KeyboardInterrupt:
    pass

GPIO.cleanup()
DB_CUR.close()
DB_CONN.close()
print('Exiting on keyboard iterrupt')
