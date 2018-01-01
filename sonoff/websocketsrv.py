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
            ## get useful data
            msg_data = json.loads(message)
            print("Websocket on_message : Message parsed")
            if self.main_config.log_level == "debug":
                pprint(msg_data)
            if "deviceid" in msg_data:
                self.device_id = msg_data["deviceid"]
            if "apikey" in msg_data:
                self.access_key = msg_data["apikey"]
            if "action" in msg_data:
                if msg_data["action"] == "update":
                   self.switch_status = msg_data["params"]["switch"]
                   self.power = msg_data["params"]["power"]

        except Exception as e:
            print("Websocket on_message : There was an error parsing the json from the command " + str(e) +
                           '  sending back ' + 'Error in JSON format.')
            return
  
        ## just forward request:
        try:
            print("Will try to forward request to central server")
            result = self.wsclient.forwardRequest(message)
            if result == "SENDFAIL" : 
                print("TODO: Will try to handle request locally" + str(e) )
                self.handleLocally(msg_data)
            elif result == "SUCC":
                print("Request forwarded to central server")
            else:
                print("The return from forward request was:"+str(result))
            return
        except Exception as e:
            print("Websocket on_message : There was an error forwarding the req. " + str(e) )

    def handleLocally(self, msg):
        if "action" in msg:
            print("TODO: Will try to handle request locally" )
            if msg["action"] == "update":
                 #TODO: store data in main on_message function
                 print("INFO: Websocketsrv.handleLocally: This is just a satus update message, sending ack")
                 confirmMsg = {"error":0,"deviceid": self.device_id ,"apikey":self.access_key }
                 self.sendMsgToRelay( json.dumps( confirmMsg ) )
            if msg["action"] == "register":
                 confirmMsg = {"error":0,"deviceid": self.device_id ,"apikey": self.access_key ,"config":{"devConfig":{"storeAppsecret":"","bucketName":"","lengthOfVideo":0,"deleteAfterDays":0,"persistentPipeline":"","storeAppid":"","uploadLimit":0,"statusReportUrl":"","storetype":0,"callbackHost":"","persistentNotifyUrl":"","callbackUrl":"","persistentOps":"","captureNumber":0,"callbackBody":""},"hb":1,"hbInterval":145}}
                 print("INFO: Websocketsrv.handleLocally: will send fake reply from central server to register command")
                 self.sendMsgToRelay( json.dumps( confirmMsg ) )
            if msg["action"] == "date":
                 ## TODO: Get actual date in correct format with python
                 confirmMsg =  {"error":0,"deviceid": self.device_id ,"apikey":self.access_key,"date":"2017-12-30T18:27:46.139Z"}


    def getRelayState(self):
        return { "power": self.power , "switch": self.switch_status }

    def _buildReplyJson(self, msg_data, code, msg):
        replyJsonDict = dict()
        try:
            if msg_data is not None:
                replyJsonDict = dict.copy(msg_data)
                #replyJsonDict["matchto"] = msg_data["matchfrom"]
                replyJsonDict["deviceid"] = self.device_id
                replyJsonDict["apikey"] = self.access_key

            else:
                # default values:
                replyJsonDict["deviceid"] = self.device_id
                replyJsonDict["apikey"] = self.access_key

            replyJson = json.dumps(replyJsonDict)
            print("_buildReplyJson : Reply json - " + replyJson)
            return replyJson

        except Exception as e:
            print("_buildReplyJson : Exception while building the json for reply " + str(e))
            return '{"protocolVersion":"3.0","responseType":"ACTION","rqRef":"102","deviceID":"1","accessKey":"NoKey",' \
                   '"accessLevel":0,"resultCode":4001,"resultMessage":"ERROR Building reply json"}'
