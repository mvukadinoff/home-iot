import paho.mqtt.client as mqtt
import time
import logging

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



class ShuttersMotorControl(object):


    def __init__(self, broker_address, broker_port=1883):
        self.client = mqtt.Client() #create new instance
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        self.client.enable_logger(logger)
        #self.client.connect(broker_address,broker_port,60) #connect to broker
        #print("Connected to " + broker_address + ":"+ str(broker_port))
        #time.sleep(1)
        #self.client.subscribe("shutters/commandreply")
        #print("Subscribed to shutters/commandreply")
        #self.client.on_message=self.on_message

        # Set up sequences of motor speeds.
        self.forward_speeds = list(range(0, MAX_SPEED, 2))

        self.forward_decel = list(range(MAX_SPEED, 0, 2))

        self.reverse_speeds = list(range(0, -MAX_SPEED, -1)) + \
                              [-MAX_SPEED] * 200 + list(range(-MAX_SPEED, 0, 1)) + [0]

        # pinShutter2closedSensor = connector.gpio3p37
        self.pinShutter2openSensor = port.PA10
        self.pinShutter2closedSensor = port.PA20
        self.pinShutter1openSensor = port.PG7
        self.pinShutter1closedSensor = port.PG6

        """Init gpio module"""
        gpio.init()

        """Set directions"""
        gpio.setcfg(self.pinShutter2openSensor, gpio.INPUT)
        gpio.setcfg(self.pinShutter2closedSensor, gpio.INPUT)
        gpio.setcfg(self.pinShutter1openSensor, gpio.INPUT)
        gpio.setcfg(self.pinShutter1closedSensor, gpio.INPUT)

        """Enable pullup resistor"""
        gpio.pullup(self.pinShutter2openSensor, gpio.PULLUP)
        gpio.pullup(self.pinShutter2closedSensor, gpio.PULLUP)
        gpio.pullup(self.pinShutter1openSensor, gpio.PULLUP)
        gpio.pullup(self.pinShutter1closedSensor, gpio.PULLUP)
        # gpio.pullup(button, gpio.PULLDOWN)     # Optionally you can use pull-down resistor

    def open(self):
        print("Opening shutters")




    def stopAllMotors(self):
        motors.setSpeeds(0, 0)


    def motor1action(self,listSpeed,intLoopProtectLimit,stopSensorPin):
        print("Motor 1 start")

try:
    motors.setSpeeds(0, 0)

    print("Motor 2 forward")
    if not gpio.input(pinShutter2closedSensor) :
        print("Already at lowest position")
        motors.setSpeeds(0, 0)
        exit(0)
    for s in test_forward_speeds:
    #for s in test_reverse_speeds:
        motors.motor2.setSpeed(s)
        time.sleep(0.005)
    loopprotect = 0
    limit = 900
    print("Right Before sensor loop:" + str(gpio.input(pinShutter2closedSensor)))
    while gpio.input(pinShutter2closedSensor) and loopprotect < limit :
        #print(gpio.input(pinShutter2closedSensor))
        time.sleep(0.2)
        loopprotect += 1
    print("Stopping motor - stop condition met - sensor or limit " + str(loopprotect))
    motors.motor2.setSpeed(0)
    print("Set speed to 0 after 1 sec in case motor didn't stop:" + str(gpio.input(pinShutter2closedSensor)))
    time.sleep(1)  ## stop again in case this fails occationally
    motors.setSpeeds(0, 0)
    if loopprotect < limit:
       print("Motor was stopped from sensor "+str(loopprotect))
    else:
       print("WARNING: Limit was reached, check sensor")

#    print("Motor 2 reverse")
#    for s in test_reverse_speeds:
#        motors.motor2.setSpeed(s)
#        time.sleep(0.005)

finally:
  # Stop the motors, even if there is an exception
  # or the user presses Ctrl+C to kill the process.
  motors.setSpeeds(0, 0)

