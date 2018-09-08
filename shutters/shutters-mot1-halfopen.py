from __future__ import print_function 
from pololu_drv8835_rpi import motors, MAX_SPEED 
import time
import OPi.GPIO as GPIO 
import wiringpi
import os
import sys

if not os.getegid() == 0:
    sys.exit('Script must be run as root')


from pyA20.gpio import gpio
from pyA20.gpio import connector
from pyA20.gpio import port



# Set up sequences of motor speeds.
test_forward_speeds = list(range(0, MAX_SPEED, 2)) 

test_forward_decel = list(range(MAX_SPEED,0,2))

test_reverse_speeds = list(range(0, -MAX_SPEED, -1))

# reverse with grad. stop
#test_reverse_speeds = list(range(0, -MAX_SPEED, -1)) + \
#  [-MAX_SPEED] * 200 + list(range(-MAX_SPEED, 0, 1)) + [0]  

#pinShutter2closedSensor = connector.gpio3p37
pinShutter2closedSensor = port.PG6

"""Init gpio module"""
gpio.init()

"""Set directions"""
gpio.setcfg(pinShutter2closedSensor, gpio.INPUT)

"""Enable pullup resistor"""
gpio.pullup(pinShutter2closedSensor , gpio.PULLUP)
#gpio.pullup(button, gpio.PULLDOWN)     # Optionally you can use pull-down resistor


try:
    motors.setSpeeds(0, 0)

    print("Motor 1 forward")
    if not gpio.input(pinShutter2closedSensor) :
        print("Already at lowest position")
        motors.setSpeeds(0, 0)
    else:
        for s in test_forward_speeds:
        #for s in test_reverse_speeds:
            motors.motor1.setSpeed(s)
            time.sleep(0.005)
        loopprotect = 0
        limit = 800
        print("Right Before sensor loop:" + str(gpio.input(pinShutter2closedSensor)))
        while gpio.input(pinShutter2closedSensor) and loopprotect < limit :
            #print(gpio.input(pinShutter2closedSensor))
            time.sleep(0.2)
            loopprotect += 1
    
        print("Stopping motor - stop condition met - sensor or limit" + str(loopprotect))
        motors.motor1.setSpeed(0)
        print("Set speed to 0 after 1 sec in case motor didn't stop:" + str(gpio.input(pinShutter2closedSensor)))
        time.sleep(1)  ## stop again in case this fails occationally
        motors.setSpeeds(0, 0)
        if loopprotect < limit:
           print("Motor was stopped from sensor")
        else:
           print("WARNING: Limit was reached, check sensor")

## Reverse for a little to open for light

    #for s in test_forward_speeds:
    for s in test_reverse_speeds:
        motors.motor1.setSpeed(s)
        time.sleep(0.005)


    loopprotect = 0
    shutterStep = 20
    while loopprotect < shutterStep :
        time.sleep(0.2)
        loopprotect += 1
    motors.motor1.setSpeed(0)
    print("Set speed to 0 after 1 sec in case motor didn't stop:" + str(gpio.input(pinShutter2closedSensor)))
    time.sleep(1)  ## stop again in case this fails occationally
    motors.setSpeeds(0, 0)


finally:
  # Stop the motors, even if there is an exception
  # or the user presses Ctrl+C to kill the process.
  motors.setSpeeds(0, 0)
