#!/usr/bin/env python

import logging
from flask import Flask, jsonify, request
from multiprocessing import Process
logging.basicConfig(level=logging.INFO)

from daikinclima.daikinclima import Daikinclima

import miio

app = Flask(__name__)
#app.config['CORS_HEADERS'] = 'Content-Type'
#cors = CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/homeiot/api/v1.0/test', methods = ['GET'])
def test():
    print(request.json)
    print(request.json)
    # json_data = request.json
    # p = Process(target=jamcore.api_stack_create, args=(json_data)) # this passes a str instead of json request object
    # p.start()

    # print request.json

    return jsonify({'Success': "Running"})

@app.route('/homeiot/api/v1.0/daikinclima/temp', methods = ['GET'])
def daikinClimaGetTemp():
    daikin = Daikinclima()
    return daikin.getTemp()


@app.route('/homeiot/api/v1.0/mirobo/status', methods = ['GET'])
def miRoboStatus():
    vac = miio.Vacuum(ip, token, start_id, debug)
    res = vac.status()
    jsonresult = {"State": res.state,"Battery": res.battery,"Fanspeed": res.fanspeed,
    "cleaning_since": res.clean_time,"Cleaned_area": res.clean_area,"DND_enabled": res.dnd  }
    return jsonresult


def main():
    app.run(host='0.0.0.0', threaded=True, debug=True)

if __name__ == "__main__":
    main()
