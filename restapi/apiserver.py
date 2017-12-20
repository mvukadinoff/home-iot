#!/usr/bin/env python

import logging
from flask import Flask, jsonify, request
from multiprocessing import Process
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
#app.config['CORS_HEADERS'] = 'Content-Type'
#cors = CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/homeiot/api/v1.0/test', methods = ['POST'])
def stack():
    print(request.json)
    print(request.json)
    # json_data = request.json
    # p = Process(target=jamcore.api_stack_create, args=(json_data)) # this passes a str instead of json request object
    # p.start()

    # print request.json

    return jsonify({'Success': "Running"})



def main():
    app.run(host='0.0.0.0', threaded=True, debug=True)

if __name__ == "__main__":
    main()