from sonoff.websockclient import Websocketclient
global webSockClientForwarder

def init():
    global webSockClientForwarder
    webSockClientForwarder = Websocketclient()

