#!/usr/bin/python3
import restapi.apiserver
import sonoff.wsclientglb
import sonoff.websockforwarder
import threading

sonoff.wsclientglb.init()
sonoffThread = threading.Thread(target=sonoff.websockforwarder.main)
print("MAIN: Starting Sonoff websocket forwarder thread")
sonoffThread.start()
print("MAIN: Starting API server")
restapi.apiserver.main()
