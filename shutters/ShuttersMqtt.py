import paho.mqtt.client as mqtt
import time

## temporary while I write the controller class
from subprocess import call

class ShuttersMqtt(object):


    def __init__(self, broker_address, broker_port=1883):
        self.client = mqtt.Client() #create new instance
        self.client.connect(broker_address,broker_port,60) #connect to broker
        print("Connected to " + broker_address + ":"+ str(broker_port))
        time.sleep(1)
        self.client.subscribe("shutters/command")
        print("Subscribed to shutters ")
        self.client.on_message=self.on_message

    def on_message(self,client, userdata, message):
        print("message received " ,str(message.payload.decode("utf-8")))
        print("message topic=",message.topic)
        print("message qos=",message.qos)
        print("message retain flag=",message.retain)
        cmd = str(message.payload.decode("utf-8"))
        if cmd == "OPEN":
            call(['python','/root/shutters-pyh3.py'])
        elif cmd == "CLOSE":
            call(['python','/root/shutters-pyh3-copy-godown.py'])
        elif cmd == "SEMIOPEN":
            call(['python','/root/shutters-pyh3-copy-halfopen.py'])
  
    def listen(self):
        #self.client.loop_start()
        self.client.loop_forever()
        print("Started mqtt loop")
        while True:
            time.sleep(4)

if __name__ == "__main__":
    shutterListener=ShuttersMqtt("192.168.1.2")
    shutterListener.listen()


