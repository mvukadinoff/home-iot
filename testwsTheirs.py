from sonoff.websockcklient import Websocketclient
#from sonoff.websocketsrv import WebSocketSrv
import json

wsclient = Websocketclient()
print("Connecting to remote WS server to forward request")
wsclient.connectToHost()

register_msg= {'action': 'register',
 'apikey': '1538c624-1d13-4cab-a0d8-319fc388ba0c',
 'deviceid': '10000bae1f',
 'model': 'PSC-B01-GL',
 'romVersion': '2.0.4',
 'ts': 1389,
 'userAgent': 'device',
 'version': 2}

wsclient.forwardRequest(json.dumps(register_msg))