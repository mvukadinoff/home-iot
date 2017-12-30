from flask import Flask, render_template, request
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from sonoff.websocketsrv import WebSocketSrv
from sonoff.websockclient import Websocketclient
from config.config import Config
import json
import requests
import threading

import sonoff.wsclientglb

flaskapp = Flask(__name__)
socket = Sockets(flaskapp)

@flaskapp.route('/')
def home():
    return render_template('main.html')

@flaskapp.route('/dispatch/device', methods = ['GET'])
def sonoffDispatchDeviceGet():
    print("REST: Relay attempts to get websocket serever address from GET /dispatch/device")
    jsonresult = {"error":0,"reason":"ok","IP":"192.168.1.2","port":443}
    return json.dumps(jsonresult)

@flaskapp.route('/dispatch/device', methods = ['POST'])
def sonoffDispatchDevicePost():
    print("REST: Relay attempts to get websocket serever address from POST /dispatch/device")
    print("got the following params: "+json.dumps(request.get_json()))
    jsonresult = {"error":0,"reason":"ok","IP":"192.168.1.2","port":443}
    ## Make the actual request to Sonoff
    try:
        sonoffDispatchDeviceForward(json.dumps(request.get_json()))
    except Exception as e:
        print("Failed to dispatch to central server, but that's ok " + str(e))
    print("REST: Returning to WiFi Relay:"+ json.dumps(jsonresult) ) 
    return json.dumps(jsonresult)

@socket.route('/api/ws')
def server_socket(ws):
    srv = WebSocketSrv(ws,sonoff.wsclientglb.webSockClientForwarder)
    # set the new socket in the client forwarder to be able to send replys
    print("Service main : Incoming websocket connection")
    while not ws.closed:
        message = ws.receive()
        sonoff.wsclientglb.webSockClientForwarder.wsToRelay = srv
        print("Set the ws srv object to :" + str(sonoff.wsclientglb.webSockClientForwarder.wsToRelay) )
        srv.on_message(message)
        print("Completed on_message now ws srv object is :" + str(sonoff.wsclientglb.webSockClientForwarder.wsToRelay) )
    print("SOCKET CONN CLOSED removing srv object")
    del srv


def sonoffDispatchDeviceForward(requestdata):
    main_config = Config()
    url = "https://" + main_config.configOpt["sonoff_server"] + ":" + main_config.configOpt["sonoff_port"] + "/dispatch/device"
    res = requests.post(url=url, data=requestdata, verify=False)
    print("Sent to " + url + " data " + requestdata  + " got back:")
    print(res.text)


def main():
    main_config = Config()
    print("Connecting to remote WS server to forward request")
    # webSockClientForwarder.connectToHost()
    t = threading.Thread(target=sonoff.wsclientglb.webSockClientForwarder.connectToHost)
    t.start()

    ws_port = int(main_config.configOpt["listen_port_websock"])
    listen_address = main_config.configOpt["listen_address"]
    print('INFO: WSforwarder main : Starting websocket listener...')
    server = pywsgi.WSGIServer((listen_address, ws_port), flaskapp, handler_class=WebSocketHandler)
    server.serve_forever()

#if __name__ == '__main__':
#    main()


