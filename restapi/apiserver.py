#!/usr/bin/env python

import logging
from flask import Flask, jsonify, request, url_for
from multiprocessing import Process
logging.basicConfig(level=logging.INFO)
import json
import urllib
from daikinclima.daikinclima import Daikinclima
import miio
# to gain access to global var object webSockClientForwarder and the communnicator to relay object: webSockClientForwarder.wsToRelay
import sonoff.wsclientglb
from config.config import Config
from shutters.controller import ShuttersController
import subprocess
import sys, traceback

app = Flask(__name__)
#app.config['CORS_HEADERS'] = 'Content-Type'
#cors = CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/homeiot/api/v1.0/test', methods = ['GET'])
def test():
    #print(request.json)
    # json_data = request.json
    # p = Process(target=jamcore.api_stack_create, args=(json_data)) # this passes a str instead of json request object
    # p.start()

    # print request.json

    return jsonify({'Success': "Running"})

@app.route('/homeiot/api/v1.0/daikinclima/temp', methods = ['GET'])
def daikinClimaGetTemp():
    daikin = Daikinclima()
    return jsonify(daikin.getTemp())

@app.route('/homeiot/api/v1.0/daikinclima/switchon', methods = ['POST'])
def daikinClimaSwitchOn():
    try:
        mode = request.form['mode']
        temp = request.form['temp']
    except Exception as e:
        print("ERROR: apiserver daikinClimaSwitchOn: Failed to get parameters " + str(e) )
    daikin = Daikinclima()
    return jsonify(daikin.switchOn(mode,temp))


@app.route('/homeiot/api/v1.0/mirobo/status', methods = ['GET'])
def miRoboStatus():
    conf = Config()
    ip=conf.configOpt["mivac_ip"]
    token=conf.configOpt["mivac_token"]
    start_id=0
    vac = miio.integrations.vacuum.roborock.RoborockVacuum(ip, token, start_id, True)
    res = vac.status()
    jsonresult = {"State": res.state,"Battery": res.battery,"Fanspeed": res.fanspeed,"cleaning_since": str(res.clean_time),"Cleaned_area": res.clean_area  }
    return jsonify(jsonresult)

@app.route('/homeiot/api/v1.0/mirobo/clean', methods = ['GET'])
def miRoboClean():
    conf = Config()
    ip=conf.configOpt["mivac_ip"]
    token=conf.configOpt["mivac_token"]
    start_id=0
    vac = miio.integrations.vacuum.roborock.RoborockVacuum(ip, token, start_id, True)
    res = vac.start()
    jsonresult = {"Response": str(res) }
    return jsonify(jsonresult)


@app.route('/homeiot/api/v1.0/mirobo/dock', methods = ['GET'])
def miRoboDock():
    conf = Config()
    ip=conf.configOpt["mivac_ip"]
    token=conf.configOpt["mivac_token"]
    start_id=0
    vac = miio.integrations.vacuum.roborock.RoborockVacuum(ip, token, start_id, True)
    res = vac.home()
    jsonresult = {"Response": str(res) }
    return jsonify(jsonresult)



@app.route('/homeiot/api/v1.0/sonoff/switch', methods = ['POST'])
def sonoffSwitch():
    try:
       #state=request.args.get('state')
       state=request.form['state']
       if state not in  [ "on" , "off" ]:
          print("Sonoff: ERROR state param not on or off, assuming off , suplied:"+ state )
          state="off"
    except:
       print("Sonoff: ERROR state param not supplied, assuming off")
       state="off"
    sonoff.wsclientglb.webSockClientForwarder.switchRelay(state)
    return '{ "status" : "Switched boiler ' + state + '" }'

@app.route('/homeiot/api/v1.0/sonoff/status', methods = ['GET'])
def sonoffStatus():
    jsonresult=sonoff.wsclientglb.webSockClientForwarder.getRelayState()
    return jsonify(jsonresult)
    
@app.route('/homeiot/api/v1.0/shutters/command', methods = ['POST'])
def shuttersCommand():
    try:
       command=request.form['command']
       conf = Config()
       broker=conf.configOpt["mqtt_broker"]
       shutters=ShuttersController(broker)
       response=shutters.ShuttersCommand(command)
       print("Shutters: sent message to mqtt broker " + broker+ " command:" + command + " " +  str(response))
    except Exception as e:
       print("RestAPIShutters: ERROR command param not supplied, please specify either OPEN,CLOSE,SEMIOPEN,UP,DOWN or error connecting " + str(e))
       response= str(e)
    return jsonify(response)

@app.route('/homeiot/api/v1.0/lights', methods = ['POST'])
def lights():
    try:
       lstate=request.form['state']
       print("Lights command received: {lstate}".format(lstate=lstate))
       conf = Config()
       light1token=conf.configOpt["milight_tok1"]
       light2token=conf.configOpt["milight_tok2"]
       light1ip=conf.configOpt["milightip1"]
       light2ip=conf.configOpt["milightip2"]

       bulb1 = miio.PhilipsBulb(light1ip,light1token)
       bulb2 = miio.PhilipsBulb(light2ip,light2token)
       if lstate == "ON":
           state="on"
           bulb1.on()
           bulb2.on()
       else:
           state="off"
           bulb1.off()
           bulb2.off()
       response= "Succesfully switched lights " + str(state)
    except Exception as e:
       print("RestAPI Lights: ERROR command param not supplied, please specify either ON or OFF in the state post variable or there was an error controlling the lights " + str(e))
       traceback.print_exc(file=sys.stdout)
       response= {"status": "error", "message": "There was an error controlling the lights: " + str(e)}
    return jsonify(response)


@app.route('/homeiot/api/v1.0/lightsdim', methods = ['GET', 'POST'])
def lightsdim():
    try:
       conf = Config()
       light1token=conf.configOpt["milight_tok1"]
       light2token=conf.configOpt["milight_tok2"]
       light1ip=conf.configOpt["milightip1"]
       light2ip=conf.configOpt["milightip2"]

       print("Lights dim command received - setting brightness to 20%, color temp to 20%")

       # Control first light using miio library
       bulb1 = miio.PhilipsBulb(light1ip, light1token)
       bulb1.on()
       bulb1.set_brightness(20)
       bulb1.set_color_temperature(20)

       # Control second light using miio library
       bulb2 = miio.PhilipsBulb(light2ip, light2token)
       bulb2.on()
       bulb2.set_brightness(20)
       bulb2.set_color_temperature(20)

       response = {"status": "success", "action": "dimmed", "brightness": 20, "color_temp": 20}
       print("Lights dimmed successfully")
    except Exception as e:
       print("RestAPI Lights Dim: ERROR - " + str(e))
       traceback.print_exc(file=sys.stdout)
       response= {"status": "error", "message": "There was an error dimming the lights: " + str(e)}
    return jsonify(response)


@app.route('/homeiot/api/v1.0/lightsbrighten', methods = ['GET', 'POST'])
def lightsbrighten():
    try:
       conf = Config()
       light1token=conf.configOpt["milight_tok1"]
       light2token=conf.configOpt["milight_tok2"]
       light1ip=conf.configOpt["milightip1"]
       light2ip=conf.configOpt["milightip2"]

       print("Lights brighten command received - setting brightness to 100%, color temp to 30%")

       # Control first light using miio library
       bulb1 = miio.PhilipsBulb(light1ip, light1token)
       bulb1.set_brightness(100)
       bulb1.set_color_temperature(30)

       # Control second light using miio library
       bulb2 = miio.PhilipsBulb(light2ip, light2token)
       bulb2.set_brightness(100)
       bulb2.set_color_temperature(30)

       response = {"status": "success", "action": "brightened", "brightness": 100, "color_temp": 30}
       print("Lights brightened successfully")
    except Exception as e:
       print("RestAPI Lights Brighten: ERROR - " + str(e))
       traceback.print_exc(file=sys.stdout)
       response= {"status": "error", "message": "There was an error brightening the lights: " + str(e)}
    return jsonify(response)


@app.route("/homeiot/")
def site_map():
    links = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = "{:20s} {}".format(methods, url)
        links.append((rule.endpoint,line))
    return json.dumps(links)


def main():
    conf = Config()
    app.run(host=conf.configOpt["listen_address"], port=int(conf.configOpt["listen_port"]), threaded=True, debug=True, use_reloader=False)

#if __name__ == "__main__":
#    main()
