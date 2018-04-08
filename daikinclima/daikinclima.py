import requests
import json
import os
from pprint import pprint


class Daikinclima:
    def __init__(self):
        ip="192.168.1.14" ## TODO: get from config
        self.url_get = "http://" + ip + '/aircon/get_control_info'
        self.url_set = "http://" + ip + '/aircon/set_control_info'
        self.url_sensor = "http://" + ip + '/aircon/get_sensor_info'
        #self.headers = {'X-Auth-Email': 'test', 'X-Auth-Key': 'test', 'Content-Type': 'application/json'}
        self.valueDict = dict()


    def getTemp(self):
        params = { "lpw": "" }
        try:
            resp = requests.get(url=self.url_sensor, params=params )
            print("INFO: dakingclima: getTemp : result : " + resp.text )
        except Exception as e:
            print("ERROR: communicating to Daikin clima : " + str(e) )
            return {"status": "ERROR" }
        if self.parseParams(resp.text):
            return {"status": "ERROR" }
        tempInner=self.valueDict["htemp"]
        tempOutter=self.valueDict["otemp"]
        return { "homeTemp": tempInner , "outTemp": tempOutter }


    def parseParams(self,paramstring):
        try:
            ## Try to parse out parameters
            valueList=paramstring.split(",")
            self.valueDict.clear()
            for val in valueList:
                key,value = val.split("=")
                self.valueDict[key] = value
        except Exception as e:
            print("ERROR: parsing temperature data : " + str(e) )
            return 1
        return 0

        #data = {"type": "A", "proxiable": True, "proxied": False,"ttl": 1}
        #resp = requests.put(url=self.url, headers=self.headers, data=json.dumps(data))
