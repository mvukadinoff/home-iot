from flask import Flask
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from sonoff.websocketsrv import WebSocketSrv
from config.config import Config


flaskapp = Flask(__name__)
socket = Sockets(flaskapp)



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


