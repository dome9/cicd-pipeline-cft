import requests
from requests.auth import HTTPBasicAuth
import json

def evaluate_cft_template(d9key, d9secret, bundleId, template, cftparams):
    print('Verify CFT using Dome9 Compliance Engine')
    print("BundleId=%s" % bundleId)
    # print("CFT=%s" % template)
    
    risk = 0
    url = "https://api.dome9.com/v2/assessment/bundleV2"

    params = convert_parameters_to_dome9_format(cftparams)
    print('using CFT parameters:%s' % params)

    d9_request_data = json.dumps({
        'Id' : bundleId,
        'Region' : 'us_east_1',
        'cft' : { 'rootName':'cft.json', 'params':params, 'files':[{'name':'cft.json', 'template': template }]}
        })
    headers = {'content-type': 'application/json'}

    response = requests.request("POST", url, data=d9_request_data, headers=headers, auth=HTTPBasicAuth(d9key, d9secret))
    # print(response.text)
    # TODO: Error handling for various issues (auth, permissions, bundle, template)
    d9resp = json.loads(response.text)
    # print(response.text)
    if 'errorMessage' in d9resp.keys(): # Evaluation error
        print('* Error during CFT evaluation: %s' % d9resp['errorMessage'])
        raise Exception(d9resp['errorMessage'])
    
    failedRules = [json.dumps({
    'name':test['rule']['name'], 
    'description':test['rule']['description'], 
    'severity':test['rule']['severity'],
    'tag': test['rule']['complianceTag']
    }) for test in d9resp['tests'] if not test['testPassed'] ]
    
    if len(failedRules) > 0:
        risk = 100 # TODO: base it on the severity of the rules - max of the severities
        print('*** Found failed rules ***')
        print(failedRules)
    else:
        print('CFT Test passed. No failed rules :)')
    url = "https://secure.dome9.com/v2/compliance-engine/result/%s" % d9resp['id']
    return risk, failedRules, url

def convert_parameters_to_dome9_format(params_str):
    """convert a json string into a list of {key, value}
    See an example for input format in my-app-cft/prod-stack-configuration.json
    """
    try:
        params = json.loads(params_str)['Parameters']
        # TODO: handle Attribute excpetions here
        return [{'key':key, 'value':params[key]} for key in params]
    except:
        print('Could not parse the parameter:%s' % params_str)
        raise
