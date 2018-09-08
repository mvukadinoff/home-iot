from __future__ import print_function 
from pololu_drv8835_rpi import motors, MAX_SPEED 
import time
import OPi.GPIO as GPIO 
import wiringpi


# Set up sequences of motor speeds.
test_forward_speeds = list(range(0, MAX_SPEED, 1)) 

test_forward_decel = list(range(MAX_SPEED,0,1))

test_reverse_speeds = list(range(0, -MAX_SPEED, -1)) + \
  [-MAX_SPEED] * 200 + list(range(-MAX_SPEED, 0, 1)) + [0]  

#GPIO.setmode(GPIO.SUNXI)
#pinMotor2 = 'PG7' #  29 (PG7) 
pinMotor2wpi = 25
# as pull up is not supported change to output high than change to in - otherwise later when support is added 
#GPIO.setup(channel, GPIO.IN ,  pull_up_down=GPIO.PUD_UP)
#GPIO.setup(channel, GPIO.OUT ,  initial=GPIO.HIGH)
#GPIO.setup(pinMotor2, GPIO.IN )

wiringpi.wiringPiSetupGpio()
wiringpi.pinMode( pinMotor2wpi , wiringpi.GPIO.INPUT )  # set mode 0 - input
print("Initial state:" + str(wiringpi.digitalRead(pinMotor2wpi)) )
wiringpi.pullUpDnControl( pinMotor2wpi ,  wiringpi.GPIO.PUD_UP)  # pull up
print("After pull up:" + str(wiringpi.digitalRead(pinMotor2wpi)) )
#wiringpi.pullUpDnControl( pinMotor2wpi ,  wiringpi.GPIO.PUD_DOWN)  # pull down
#print("After pull down:" + str(wiringpi.digitalRead(pinMotor2wpi)) )


try:
    motors.setSpeeds(0, 0)

    print("Motor 2 forward")
    if not wiringpi.digitalRead(pinMotor2wpi) :
        print("Already at lowest position")
        motors.setSpeeds(0, 0)
        exit(0)
    for s in test_forward_speeds:
        motors.motor2.setSpeed(s)
        time.sleep(0.005)
    loopprotect = 0
    limit = 100000
    print("Right Before sensor loop:" + str(wiringpi.digitalRead(pinMotor2wpi)) )
    while wiringpi.digitalRead(pinMotor2wpi) and loopprotect < limit :
        print(wiringpi.digitalRead(pinMotor2wpi))
        time.sleep(0.4)
        loopprotect += 1

    motors.motor2.setSpeed(0)
    motors.setSpeeds(0, 0)


#    print("Motor 2 reverse")
#    for s in test_reverse_speeds:
#        motors.motor2.setSpeed(s)
#        time.sleep(0.005)

finally:
  # Stop the motors, even if there is an exception
  # or the user presses Ctrl+C to kill the process.
  motors.setSpeeds(0, 0)
