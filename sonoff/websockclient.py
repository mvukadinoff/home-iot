import json
from config.config import Config
from websocket import create_connection

global access_key
global device_id
global wsclnt


def _send_json_cmd(str_json_cmd):
    try:
        wsclnt.send(str_json_cmd)
    except Exception, e:
        print("ZioLib _send_json_cmd : Error occurred while trying to send command, check if "
                       "connection was established " + str(e))
    # wait for reply as per requirement
    main_config = Config()
    wsclnt.settimeout(float(30))
    try:
        result = wsclnt.recv()
    except Exception, e:
        print(" _send_json_cmd : Error getting back result, it's possible that the "
                       "timeout was reached " + str(e))
        result = "ERROR"
    return result



def forwardRequest(json_string):
    try:
        msg_dict = json.loads(json_string)
    except:
        print(" forwardRequest : Failed to parse json, please check the passed argument")
        return "ERROR"
    ## modify json if needed
    msg_dict["accessKey"] = access_key
    try:
        jsoncmd = json.dumps(msg_dict)
    except:
        print(" forwardRequest : Failed to build json")
        return "ERROR"
    return _send_json_cmd(jsoncmd)
