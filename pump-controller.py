# imports
import RPi.GPIO as GPIO

# set GPIO pin numbering scheme
GPIO.setmode(GPIO.BCM)

# setup pin directions

# Relay control (BCM 17, header 11)
GPIO.setup(17, GPIO.OUT)

# Override switch (BCM 27, header 13)
GPIO.setup(27, GPIO.IN)

# Temperature sensor (Uses one-wire protocol...tutorial suggests BCM 4)
# https://pinout.xyz/pinout/1_wire#
# https://thepihut.com/blogs/raspberry-pi-tutorials/18095732-sensors-temperature-with-the-1-wire-interface-and-the-ds18b20

# Now let's setup the iterrupt callback function

