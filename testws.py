#from sonoff.websockcklient import Websocketclient
#from sonoff.websocketsrv import WebSocketSrv


import sonoff.websockforwarder
import sonoff.wsclientglb
sonoff.wsclientglb.init()
sonoff.websockforwarder.main()

#webSockClientForwarder.connectToHost()
