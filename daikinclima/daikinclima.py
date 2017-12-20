import requests
import json
import os


class Daikinclima:
    def __init__(self):
        ip="192.168.1.4" ## TODO: get from config
        url = ip + '/zones/' + '/dns_records?per_page=1000'
        headers = {'X-Auth-Email': 'test', 'X-Auth-Key': 'test', 'Content-Type': 'application/json'}


    def getTemp(self):
        resp = requests.get(url=self.url, headers=self.headers)
        data = {"type": "A", "proxiable": True, "proxied": False,"ttl": 1}
        resp = requests.put(url=self.url, headers=self.headers, data=json.dumps(data))

