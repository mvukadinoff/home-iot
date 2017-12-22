import json
import threading
import imp
import os
import random
from config.config import Config
from pprint import pprint
import sys

class WebSocketSrv(object):
    def __init__(self, ws):
        self.ws = ws
        self.main_config = Config()
        self.access_key = ""
        self.device_id = ""

    def on_message(self, message):
        """
        :param message: the message send via websocket - string in json format
        :return: no value
        """
        print("Websocket on_message : We got a message from controller")

        if message is None:
            print("Websocket on_message : Empty message received. Skipping.")
            return

        try:
            msg_data = json.loads(message)
            print("Websocket on_message : Message parsed")
            if self.main_config.log_level == "debug":
                pprint(msg_data)

        except Exception, e:
            print("Websocket on_message : There was an error parsing the json from the command " + str(e) +
                           '  sending back ' + 'Error in JSON format.')
            return


        if msg_data["operation"] == "ACTION":
            print("Websocket on_message: actionname " + msg_data["actionName"])

            if msg_data["actionName"] == "triggerscript":
                try:
                    self.script_trigger(msg_data)

                except Exception, e:
                    LoggerSE.print_traceback(self.main_config.log_level)
                    error_reply = self._buildReplyJson(msg_data, code=4002, msg='Error triggering script')
                    LoggerSE.error("Websocket triggerscript : There was an error calling the action " + str(e) +
                                   ' sending back - ' + error_reply)
                    self.ws.send(error_reply)
                    return

            elif msg_data["actionName"] == "downloadscript":
                try:
                    # Validate if all required JSON fields are present
                    if "url" not in msg_data["actionParam"]:
                        error_reply = self._buildReplyJson(msg_data, code=1017, msg="Missing argument")
                        LoggerSE.error("Websocket downloadscript : Incorrect JSON format, missing field "
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
                        LoggerSE.error("Websocket downloadscript : FAIL - Script download failed - "
                                       ' sending back - ' + error_reply)
                        self.ws.send(error_reply)
                        return

                except Exception, e:
                    error_reply = self._buildReplyJson(msg_data, code=4010, msg="FAIL - Script download failed")
                    LoggerSE.print_traceback(self.main_config.log_level)
                    LoggerSE.error("Websocket downloadscript : Error in downloadscript" + str(e) +
                                   ' sending back - ' + error_reply)
                    self.ws.send(error_reply)
                    return

            elif msg_data["actionName"] == "deletescript":
                try:
                    # Validate if all required JSON fields are present
                    if "scriptName" not in msg_data["actionParam"]:
                        error_reply = self._buildReplyJson(msg_data, code=1017, msg="Missing argument")
                        LoggerSE.error("Websocket deletescript : Incorrect JSON format, missing field "
                                       " sending back - " + error_reply)
                        self.ws.send(error_reply)
                        return

                    if "User" not in msg_data["actionParam"] or \
                                        "Password" not in msg_data["actionParam"]:
                        admin_user = ""
                        admin_pass = ""
                    else:
                        admin_user = msg_data["actionParam"]["User"]
                        admin_pass = msg_data["actionParam"]["Password"]

                    script_name = msg_data["actionParam"]["scriptName"]

                    if self.command.delete_script(admin_user, admin_pass, script_name):
                        self.ws.send(self._buildReplyJson(msg_data, code=200, msg="OK - script deleted"))
                        return

                    else:
                        error_reply = self._buildReplyJson(msg_data, code=4007, msg="Script instance not found")
                        LoggerSE.error("Websocket deletescript : No such file in script dir - " + script_name + ".py"
                                       ' sending back - ' + error_reply)
                        self.ws.send(error_reply)
                        return

                except Exception, e:
                    error_reply = self._buildReplyJson(msg_data, code=4007, msg="Script instance not found")
                    LoggerSE.print_traceback(self.main_config.log_level)
                    LoggerSE.error("Websocket deletescript : Error in deletescript" + str(e) +
                                   ' sending back - ' + error_reply)
                    self.ws.send(error_reply)
                    return

            elif msg_data["actionName"] == "config":
                try:
                    # Validate if all required JSON fields are present
                    if "paramName" not in msg_data["actionParam"] or \
                                    "paramValue" not in msg_data["actionParam"]:

                        error_reply = self._buildReplyJson(msg_data, code=1017, msg="Missing argument")
                        LoggerSE.error("Websocket change_config : Incorrect JSON format, missing field "
                                       " sending back - " + error_reply)
                        self.ws.send(error_reply)
                        return

                    if "User" not in msg_data["actionParam"] or "Password" not in msg_data["actionParam"]:
                        admin_user = ""
                        admin_pass = ""
                    else:
                        admin_user = msg_data["actionParam"]["User"]
                        admin_pass = msg_data["actionParam"]["Password"]

                    conf_property = msg_data["actionParam"]["paramName"]
                    new_value = msg_data["actionParam"]["paramValue"]

                    if self.command.change_config(admin_user, admin_pass, conf_property, new_value):
                        self.ws.send(self._buildReplyJson(msg_data, code=200, msg="OK - Parameter changed"))
                        self.main_config.rereadconf()
                        # Reload logger in case loging facility was changed TODO: do a check for loging options
                        imp.reload(sys.modules["LoggerSE"])
                        return

                    else:
                        error_reply = self._buildReplyJson(msg_data, code=4011, msg="FAIL - Parameter not existing")
                        LoggerSE.error("Websocket change_config : Config parameter does not exit - " + conf_property +
                                       ' sending back - ' + error_reply)
                        self.ws.send(error_reply)
                        return

                except Exception, e:
                    error_reply = self._buildReplyJson(msg_data, code=4011, msg="FAIL - Parameter not existing")
                    LoggerSE.print_traceback(self.main_config.log_level)
                    LoggerSE.error("Websocket change_config : Error in action change_config" + str(e) +
                                   ' sending back - ' + error_reply)
                    self.ws.send(error_reply)
                    return

            elif msg_data["actionName"] == "deletelock":
                try:
                    # Validate if all required JSON fields are present
                    if "User" not in msg_data["actionParam"] or "Password" not in msg_data["actionParam"]:
                        # error_reply = self._buildReplyJson(msg_data, code=1017, msg="Missing argument")
                        # LoggerSE.error("Websocket deletelock : Incorrect JSON format, missing field "
                        #               " sending back - " + error_reply)
                        # self.ws.send(error_reply)
                        admin_user = ""
                        admin_pass = ""
                    else:
                        admin_user = msg_data["actionParam"]["User"]
                        admin_pass = msg_data["actionParam"]["Password"]

                    if self.command.delete_lock(admin_user, admin_pass):
                        self.ws.send(self._buildReplyJson(msg_data, code=200, msg="OK - Lock file removed"))
                        return

                    else:
                        error_reply = self._buildReplyJson(msg_data, code=4012, msg="FAIL - Unable to remove lock file")
                        LoggerSE.error("Websocket deletelock : FAIL - Unable to remove lock file - "
                                       ' sending back - ' + error_reply)
                        self.ws.send(error_reply)
                        return

                except Exception, e:
                    error_reply = self._buildReplyJson(msg_data, code=4012, msg="FAIL - Unable to remove lock file")
                    LoggerSE.print_traceback(self.main_config.log_level)
                    LoggerSE.error("Websocket deletelock : Error in action deletelock" + str(e) +
                                   ' sending back - ' + error_reply)
                    self.ws.send(error_reply)
                    return

            elif msg_data["actionName"] == "changepass":
                try:
                    # Validate if all required JSON fields are present
                    if "NewPassword" not in msg_data["actionParam"]:
                        error_reply = self._buildReplyJson(msg_data, code=1017, msg="Missing argument")
                        LoggerSE.error("Websocket changepass : Incorrect JSON format, missing field "
                                       " sending back - " + error_reply)
                        self.ws.send(error_reply)
                        return

                    if "User" not in msg_data["actionParam"] or "Password" not in msg_data["actionParam"]:
                        # error_reply = self._buildReplyJson(msg_data, code=1017, msg="Missing argument")
                        # LoggerSE.error("Websocket deletelock : Incorrect JSON format, missing field "
                        #               " sending back - " + error_reply)
                        # self.ws.send(error_reply)
                        admin_user = ""
                        admin_pass = ""
                    else:
                        admin_user = msg_data["actionParam"]["User"]
                        admin_pass = msg_data["actionParam"]["Password"]

                    new_pass = msg_data["actionParam"]["NewPassword"]

                    if self.command.change_admin_pass(admin_user, admin_pass, new_pass):
                        self.ws.send(self._buildReplyJson(msg_data, code=200, msg="OK - Password changed successfully"))
                        return

                    else:
                        error_reply = self._buildReplyJson(msg_data, code=4013, msg="FAIL - Unable to change password")
                        LoggerSE.error("Websocket changepass : FAIL - Unable to change password - "
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
            LoggerSE.debug("_buildReplyJson : Reply json - " + replyJson)
            return replyJson

        except Exception, e:
            LoggerSE.debug("_buildReplyJson : Exception while building the json for reply " + str(e))
            LoggerSE.print_traceback(self.main_config.log_level)
            return '{"protocolVersion":"3.0","responseType":"ACTION","rqRef":"102","deviceID":"1","accessKey":"NoKey",' \
                   '"accessLevel":0,"resultCode":4001,"resultMessage":"ERROR Building reply json"}'
