import paho.mqtt.client as mqtt
import time
import logging
from ShuttersMotorControl import ShuttersMotorControl
## temporary while I write the controller class
from subprocess import call

class ShuttersMqtt(object):


    def __init__(self, broker_address, broker_port=1883):
        self.client = mqtt.Client(client_id="shutters", clean_session=False) #create new instance
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        self.client.enable_logger(logger)
        self.client.connect(broker_address,broker_port,60) #connect to broker
        print("Connected to " + broker_address + ":"+ str(broker_port))
        time.sleep(1)
        self.client.subscribe("shutters/command")
        print("Subscribed to shutters ")
        self.client.on_message=self.on_message
        self.motcontrol = ShuttersMotorControl()

    def on_message(self,client, userdata, message):
        print("message received " ,str(message.payload.decode("utf-8")))
        print("message topic=",message.topic)
        print("message qos=",message.qos)
        print("message retain flag=",message.retain)
        cmd = str(message.payload.decode("utf-8"))
        if cmd == "OPEN":
            self.motcontrol.open()
            #call(['python','/root/shutters-pyh3.py'])
            #call(['python','/root/shutters-mot1-pyh3-copy-goup.py'])
        elif cmd == "CLOSE":
            self.motcontrol.close()
            #call(['python','/root/shutters-pyh3-copy-godown.py'])
            #call(['python','/root/shutters-mot1-pyh3-copy-godown.py'])
        elif cmd == "SEMIOPEN":
            self.motcontrol.halfopen()
            #call(['python','/root/shutters-pyh3-copy-halfopen.py'])
            #call(['python','/root/shutters-mot1-halfopen.py'])
  
    def listen(self):
        #self.client.loop_start()
        self.client.loop_forever()
        print("Started mqtt loop")
        while True:
            time.sleep(4)

if __name__ == "__main__":
    bNotConnected=True
    while bNotConnected:
        try:
            shutterListener=ShuttersMqtt("192.168.1.2")
            bNotConnected=False
        except Exception as e:
            print("Failed to connecto to broker "  + str(e) )
            print("Will try to reconnect")
            time.sleep(15)
    shutterListener.listen()


