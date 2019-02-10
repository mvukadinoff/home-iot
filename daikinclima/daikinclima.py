import requests
import json
import os
from pprint import pprint
from config.config import Config

class Daikinclima:
    def __init__(self):
        conf = Config()
        ip=conf.configOpt["daikin_ip"]
        #ip="192.168.1.14" ## TODO: get from config
        self.url_get = "http://" + ip + '/aircon/get_control_info'
        self.url_set = "http://" + ip + '/aircon/set_control_info'
        self.url_sensor = "http://" + ip + '/aircon/get_sensor_info'
        #self.headers = {'X-Auth-Email': 'test', 'X-Auth-Key': 'test', 'Content-Type': 'application/json'}
        self.valueDict = dict()

    def switchOn(self,mode,temp):
        if mode == "HEAT":
            power = 1
            mode = 4
        elif mode == "COOL":
            power = 1
            mode = 4
        elif mode == "OFF":
            power = 0
            mode = 4
        else:
            return { "ERROR" : "Unsuported mode - chose from HEAT COOL OFF" }
        params = { "lpw": "" , "dh2":50 , "dfd4":0 , "b_stemp" : temp , "alert": 255 , "f_dir" :0 , 
		"b_shum":0 , "dh4":0 , "pow": power , "dfd3":0 , "dh3":0 , "dfd2":0 , "dfr2":5 , 
		"dfr7":5 , "dfr4":3 , "dfd7":0 , "dfrh":5 , "dt3":25.0 , "dfdh":0 , "adv":0 , 
		"dh1":"AUTO" , "dh5":0 , "dfr6":5 , "dt5":21.0 , "dfr1":5 , "stemp": temp , 
                "shum":0 , "dfd6":0 , "f_rate":3 , "b_f_dir":0 , "dt1": temp , "dhh":50 , 
		"en_demand":0 , "dfd1":0 , "dfr3":5 , "dh7": "AUTO" , "dmnd_run":0 , "mode":4 , 
		"dfd5":0, "b_mode":4 , "dt4": temp , "b_f_rate":3 , "dt7":25.0 , "dt2":"M" , "dfr5":3 }
        try:
            resp = requests.get(url=self.url_set, params=params )
            print("INFO: dakingclima: switchOn : result : " + resp.text )
        except Exception as e:
            print("ERROR: communicating to Daikin clima : " + str(e) )
            return {"status": "ERROR" }
        return resp.text


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
