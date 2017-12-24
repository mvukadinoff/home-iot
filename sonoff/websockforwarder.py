from flask import Flask, render_template, request
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from sonoff.websocketsrv import WebSocketSrv
from config.config import Config
import json

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
    print("got the following params: "+request.get_json())
    jsonresult = {"error":0,"reason":"ok","IP":"192.168.1.2","port":443}
    return json.dumps(jsonresult)

@socket.route('/')
def server_socket(ws):
    srv = WebSocketSrv(ws)
    print("Service main : Incoming websocket connection")
    while not ws.closed:
        message = ws.receive()
        srv.on_message(message)
    del srv

def main():
    main_config = Config()

    ws_port = int(main_config.configOpt["listen_port_websock"])
    listen_address = main_config.configOpt["listen_address"]
    print('Service main : Starting websocket listener...')
    server = pywsgi.WSGIServer((listen_address, ws_port), flaskapp, handler_class=WebSocketHandler)
    server.serve_forever()

if __name__ == '__main__':
    main()


