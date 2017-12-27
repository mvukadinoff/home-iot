import restapi.apiserver
import sonoff.websockforwarder
import threading

global webSockClientForwarder
sonoffThread = threading.Thread(target=sonoff.websockforwarder.main)
print("Starting Sonoff websocket forwarder thread")
sonoffThread.start()
print("Starting API server")
restapi.apiserver.main()
