import json
import threading
import imp
import os
import random
from config.config import Config
from sonoff.websockclient import Websocketclient
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

        except Exception as e:
            print("Websocket on_message : There was an error parsing the json from the command " + str(e) +
                           '  sending back ' + 'Error in JSON format.')
            return

        ## Try to reply with api-key:
        # register_callback = {"error":0, "deviceid":"10000bae1f","apikey":"1538c624-1d13-4cab-a0d8-319fc388ba0c" }
        # print("Try to send back :" + json.dumps(register_callback))
        # self.ws.send(json.dumps(register_callback))

        ## just forward request:
        try:
            print("Will try to forward request to central server")
            result = self.wsclient.forwardRequest(message)
            print("Sending back remote result to relay: " + str(result))
            self.ws.send(result)
        except Exception as e:
            print("Websocket on_message : There was an error connecting " + str(e) )


        if msg_data["operation"] == "ACTION":
            print("Websocket on_message: actionname " + msg_data["actionName"])

            if msg_data["actionName"] == "triggerscript":
                try:
                    self.script_trigger(msg_data)

                except Exception as e:
                    error_reply = self._buildReplyJson(msg_data, code=4002, msg='Error triggering script')
                    print("Websocket triggerscript : There was an error calling the action " + str(e) +
                                   ' sending back - ' + error_reply)
                    self.ws.send(error_reply)
                    return

            elif msg_data["actionName"] == "downloadscript":
                try:
                    # Validate if all required JSON fields are present
                    if "url" not in msg_data["actionParam"]:
                        error_reply = self._buildReplyJson(msg_data, code=1017, msg="Missing argument")
                        print("Websocket downloadscript : Incorrect JSON format, missing field "
                                       " sending back - " + error_reply)
                        self.ws.send(error_reply)
                        return

                    if "User" not in msg_data["actionParam"] or "Password" not in msg_data["actionParam"]:
                        admin_user = ""
                        admin_pass = ""
                    else:
                        admin_user = msg_data["actionParam"]["User"]
                        admin_pass = msg_data["actionParam"]["Password"]

                    download_url = msg_data["actionParam"]["url"]

                    if "scriptName" not in msg_data["actionParam"]:
                        script_name = ""
                    else:
                        script_name = msg_data["actionParam"]["scriptName"]

                    if self.command.download_script(admin_user, admin_pass, download_url, script_name):
                        self.ws.send(self._buildReplyJson(msg_data, code=200, msg="script downloaded"))
                        return

                    else:
                        error_reply = self._buildReplyJson(msg_data, code=4010, msg="FAIL - Script download failed")
                        print("Websocket downloadscript : FAIL - Script download failed - "
                                       ' sending back - ' + error_reply)
                        self.ws.send(error_reply)
                        return

                except Exception as e:
                    error_reply = self._buildReplyJson(msg_data, code=4010, msg="FAIL - Script download failed")
                    print("Websocket downloadscript : Error in downloadscript" + str(e) +
                                   ' sending back - ' + error_reply)
                    self.ws.send(error_reply)
                    return

    def _buildReplyJson(self, msg_data, code, msg):
        replyJsonDict = dict()
        try:
            if msg_data is not None:
                # replyJsonDict["responseType"] = msg_data["operation"]
                # replyJsonDict["rqRef"] = msg_data["rqRef"]
                # replyJsonDict["accessKey"] = msg_data["accessKey"]
                # replyJsonDict["accessLevel"] = msg_data["accessLevel"]
                # replyJsonDict["deviceID"] = msg_data["deviceID"]
                # Directly return all passed params
                replyJsonDict = dict.copy(msg_data)

            else:
                # default values:
                replyJsonDict["protocolVersion"] = "3.0"
                replyJsonDict["responseType"] = "ACTION"
                replyJsonDict["rqRef"] = 0
                replyJsonDict["accessKey"] = "NoKey"
                replyJsonDict["accessLevel"] = 0
                replyJsonDict["deviceID"] = 0

            replyJsonDict["resultCode"] = code
            replyJsonDict["resultMessage"] = msg

            replyJson = json.dumps(replyJsonDict)
            print("_buildReplyJson : Reply json - " + replyJson)
            return replyJson

        except Exception as e:
            print("_buildReplyJson : Exception while building the json for reply " + str(e))
            return '{"protocolVersion":"3.0","responseType":"ACTION","rqRef":"102","deviceID":"1","accessKey":"NoKey",' \
                   '"accessLevel":0,"resultCode":4001,"resultMessage":"ERROR Building reply json"}'
