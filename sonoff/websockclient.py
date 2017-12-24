import json
from config.config import Config
from websocket import create_connection


class Websocketclient(object):
    def _init__(self):
        self.wsclnt = ""

    def connectToHost(self,host=None, port=None):
        main_config = Config()
        if host is None:
            host = main_config.configOpt["sonoff_ws_server"]
        if port is None:
            port = main_config.configOpt["sonoff_ws_port"]
        # Connect to Zio Host
        addr = "wss://" + host + ":" + port
        print( "Will attempt to connect to " + addr )
        #self.wsclnt = self.wsclnt.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
        self.wsclnt = create_connection(addr)

    def _send_json_cmd(self,str_json_cmd):
        try:
            self.wsclnt.send(str_json_cmd)
        except Exception as e:
            print("ZioLib _send_json_cmd : Error occurred while trying to send command, check if "
                           "connection was established " + str(e))
        # wait for reply as per requirement
        main_config = Config()
        self.wsclnt.settimeout(float(30))
        try:
            result = self.wsclnt.recv()
        except Exception as e:
            print(" _send_json_cmd : Error getting back result, it's possible that the "
                           "timeout was reached " + str(e))
            result = "ERROR"
        return result



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
