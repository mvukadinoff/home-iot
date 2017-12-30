import json
import threading
import imp
import os
import random
from config.config import Config
from pprint import pprint
import sys

class WebSocketSrv(object):
    #def __init__(self, ws):
    #    self.ws = ws
    #    self.main_config = Config()
    #    self.access_key = ""
    #    self.device_id = ""

    def __init__(self, ws, ws_forwarder):
        self.ws = ws
        self.main_config = Config()
        self.access_key = ""
        self.device_id = ""
        self.wsclient = ws_forwarder

    def sendMsgToRelay(self, message):
        print("websocksrv: sendMsgToRelay: Sending back remote result to relay: " + str(message))
        self.ws.send(message)

    def switch(self,state="on"):
        jsoncmd = {"action":"update","deviceid":self.device_id,"apikey":self.access_key,"userAgent":"app","sequence":"1514400069310","ts":0,"params":{"switch":state},"from":"app"}
        self.sendMsgToRelay(json.dumps(jsoncmd))

    def on_message(self, message):
        """
        :param message: the message send via websocket - string in json format
        :return: no value
        """
        print("Websocket on_message : We got a message from relay")

        if message is None:
            print("Websocket on_message : Empty message received. Skipping.")
            return

        try:
            msg_data = json.loads(message)
            print("Websocket on_message : Message parsed")
            if self.main_config.log_level == "debug":
                pprint(msg_data)
            if "deviceid" in msg_data:
                self.device_id = msg_data["deviceid"]
            if "apikey" in msg_data:
                self.access_key = msg_data["apikey"]

        except Exception as e:
            print("Websocket on_message : There was an error parsing the json from the command " + str(e) +
                           '  sending back ' + 'Error in JSON format.')
            return

        ## just forward request:
        try:
            print("Will try to forward request to central server")
            result = self.wsclient.forwardRequest(message)
            print("Request forwarded to central server")
            return
        except Exception as e:
            print("Websocket on_message : There was an error forwarding the req. " + str(e) )



    def _buildReplyJson(self, msg_data, code, msg):
        replyJsonDict = dict()
        try:
            if msg_data is not None:
                # replyJsonDict["matchto"] = msg_data["matchfrom"]
                replyJsonDict = dict.copy(msg_data)

            else:
                # default values:
                replyJsonDict["matchto"] = "matchtovalue"

            replyJson = json.dumps(replyJsonDict)
            print("_buildReplyJson : Reply json - " + replyJson)
            return replyJson

        except Exception as e:
            print("_buildReplyJson : Exception while building the json for reply " + str(e))
            return '{"protocolVersion":"3.0","responseType":"ACTION","rqRef":"102","deviceID":"1","accessKey":"NoKey",' \
                   '"accessLevel":0,"resultCode":4001,"resultMessage":"ERROR Building reply json"}'
