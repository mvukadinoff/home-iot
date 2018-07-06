# home-iot

apt install python-pip python-wheel python-dev



# For shutters controller
download drv8835-motor-driver-rpi
drv8835-motor-driver-rpi# python setup.py install

   69  cd /usr/local/bin/WiringOP/
   77  make install
   78  cd ../WiringPi-Python-OP/
   80  python setup.py  install

# Replacement 
git clone https://github.com/duxingkei33/orangepi_PC_gpio_pyH3

  136  cd orangepi_PC_gpio_pyH3/
  138  python setup.py install
  139  history 
  140  history | tail -20

root@orangepilite:~# diff /usr/local/lib/python2.7/dist-packages/wiringpi-2.32.1-py2.7-linux-armv7l.egg/wiringpi.py ~/wiringpi.py 
679a680
>   SOFT_PWM_OUTPUT = 4;
root@orangepilite:~# diff /usr/local/lib/python2.7/dist-packages/pololu_drv8835_rpi ~/wiringpi.py 
pololu_drv8835_rpi-2.0.0.egg-info  pololu_drv8835_rpi.py              pololu_drv8835_rpi.pyc
root@orangepilite:~# diff /usr/local/lib/python2.7/dist-packages/pololu_drv8835_rpi.py ~/pololu_drv8835_rpi.py 
15,16c15,16
<   wiringpi.pinMode(12, wiringpi.GPIO.PWM_OUTPUT)
<   wiringpi.pinMode(13, wiringpi.GPIO.PWM_OUTPUT)
---
>   wiringpi.pinMode(12, wiringpi.GPIO.SOFT_PWM_OUTPUT)
>   wiringpi.pinMode(13, wiringpi.GPIO.SOFT_PWM_OUTPUT)
46c46,47
<         wiringpi.pwmWrite(self.pwm_pin, speed)
---
>         wiringpi.softPwmCreate(self.pwm_pin, 0, 500)
>         wiringpi.softPwmWrite(self.pwm_pin, speed)
root@orangepilite:~# cp /usr/local/lib/python2.7/dist-packages/pololu_drv8835_rpi.py ~/pololu_drv8835_rpi.py-original
root@orangepilite:~# cp /usr/local/lib/python2.7/dist-packages/wiringpi-2.32.1-py2.7-linux-armv7l.egg/wiringpi.py ~/wiringpi.py-original
root@orangepilite:~# 
root@orangepilite:~# cp ~/wiringpi.py /usr/local/lib/python2.7/dist-packages/wiringpi-2.32.1-py2.7-linux-armv7l.egg/wiringpi.py
root@orangepilite:~# cp ~/pololu_drv8835_rpi.py /usr/local/lib/python2.7/dist-packages/pololu_drv8835_rpi.py

