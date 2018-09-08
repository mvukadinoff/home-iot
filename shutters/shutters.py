from __future__ import print_function
import time
from pololu_drv8835_rpi import motors, MAX_SPEED
import time
import OPi.GPIO as GPIO
import wiringpi


# Set up sequences of motor speeds.
test_forward_speeds = list(range(0, MAX_SPEED, 1)) 

test_forward_decel = list(range(MAX_SPEED,0,1))

test_reverse_speeds = list(range(0, -MAX_SPEED, -1)) + \
  [-MAX_SPEED] * 200 + list(range(-MAX_SPEED, 0, 1)) + [0]  

GPIO.setmode(GPIO.SUNXI)
pinMotor2 = 'PA20' #  GPIO25 (PA20) 
pinMotor2wpi = 25
# as pull up is not supported change to output high than change to in - otherwise later when support is added 
#GPIO.setup(channel, GPIO.IN ,  pull_up_down=GPIO.PUD_UP)
#GPIO.setup(channel, GPIO.OUT ,  initial=GPIO.HIGH)
GPIO.setup(pinMotor2, GPIO.IN )

wiringpi.wiringPiSetupGpio()
wiringpi.pinMode( pinMotor2wpi , 0)  # set mode 0 - input
wiringpi.pullUpDnControl( pinMotor2wpi , 2)  # pull up


try:
    motors.setSpeeds(0, 0)

    print("Motor 2 forward")
    if GPIO.input(pinMotor2) == GPIO.LOW :
        print("Already at lowest position")
        exit(0)
    for s in test_forward_speeds:
        motors.motor2.setSpeed(s)
        time.sleep(0.005)
    loopprotect = 0
    limit = 1000000
    while GPIO.input(pinMotor2) == GPIO.HIGH and loopprotect < limit :
        time.sleep(0.1)
        loopprotect += 1

    motors.motor2.setSpeed(0)


#    print("Motor 2 reverse")
#    for s in test_reverse_speeds:
#        motors.motor2.setSpeed(s)
#        time.sleep(0.005)

finally:
  # Stop the motors, even if there is an exception
  # or the user presses Ctrl+C to kill the process.
  motors.setSpeeds(0, 0)
