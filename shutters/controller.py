import paho.mqtt.client as mqtt

class ShuttersController(object):


    def __init__(self, broker_address, broker_port=1883, client_instance="P1"):
        self.client = mqtt.Client(client_instance) #create new instance
        self.client.connect(broker_address,port=broker_port) #connect to broker


    def ShuttersCommand(self, cmd):
        if cmd not in  [ "OPEN","CLOSE","SEMIOPEN","UP","DOWN" ]:
            print("ERROR: ShuttersController.ShuttersCommand wrong command supplied "+cmd+", please specify either OPEN,CLOSE,SEMIOPEN,UP,DOWN")
            return { shutters: "wrong command supplied "+cmd+", please specify either OPEN,CLOSE,SEMIOPEN,UP,DOWN" }
        self.client.publish("shutters/command",cmd)#publish
        return {"shutters" : "command accepted" }

