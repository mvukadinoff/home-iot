import json
import ssl
from config.config import Config
from websocket import create_connection, enableTrace
import websocket
from pprint import pprint
import threading

class Websocketclient(object):
    def _init__(self):
        self.wsclnt = ""
        self.wsToRelay = ""

    def on_error(self, ws,error):
        print("ERROR: websocketclient: There was an error coomunicating to central server")
        print(error)

    def on_message(self, ws, message):
        print("Got message from central server:" + str(message))
        print("Will now forward to WiFi relay")
        self.wsToRelay.sendMsgToRelay(message)

    def connectToHost(self,host=None, port=None):
        main_config = Config()
        if host is None:
            host = main_config.configOpt["sonoff_ws_server"]
        if port is None:
            port = main_config.configOpt["sonoff_ws_port"]
        # Connect to Zio Host
        addr = "wss://" + host + ":" + port + "/api/ws"
        print( "Will attempt to connect to " + addr )
        websocket.enableTrace(False)
        try:
            #self.wsclnt = create_connection(addr, sslopt={"cert_reqs": ssl.CERT_NONE} )
            self.wsclnt = websocket.WebSocketApp( addr,  on_error = self.on_error ,on_message = self.on_message )
            self.wsclnt.run_forever( sslopt={"cert_reqs": ssl.CERT_NONE} )
            print( "Connection should have been established, but now ended")
        except Exception as e:
            print("ERROR: websocket client: connectToHost: Failed to connect " + str(e))


    def _send_json_cmd(self,str_json_cmd):
        try:
            print("Trying to send " + str_json_cmd)
            self.wsclnt.send(str_json_cmd)
        except Exception as e:
            print("_send_json_cmd : Error occurred while trying to send command, check if "
                           "connection was established " + str(e))
            print("_send_json_cmd : will try to reconnect")
            try:
                t = threading.Thread(target=self.connectToHost)
                t.start()
            except Exception as e:
                print("_send_json_cmd : Error occurred while trying to reconnect: " + str(e) )

        ## ToDO wait in thread for this: (recv)
        # wait for reply as per requirement
        #self.wsclnt.settimeout(float(30))
        #try:
        #    print("will wait for reply")
        #    result = "no answer"
        #    #result = self.wsclnt.recv()
        #except Exception as e:
        #    print(" _send_json_cmd : Error getting back result, it's possible that the "
        #                   "timeout was reached " + str(e))
        #    result = "ERROR"
        #return result
        return 0



    def forwardRequest(self,json_string):
        try:
            msg_dict = json.loads(json_string)
        except:
            print(" forwardRequest : Failed to parse json, please check the passed argument")
            return "ERROR"
        ## modify json if needed
        #msg_dict["accessKey"] = "test"
        try:
            jsoncmd = json.dumps(msg_dict)
        except:
            print(" forwardRequest : Failed to build json")
            return "ERROR"
        return self._send_json_cmd(jsoncmd)
