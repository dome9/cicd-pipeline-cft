import requests
from requests.auth import HTTPBasicAuth
import json
import uuid


def evaluate_cft_template(d9_key, d9_secret, bundle_id, template, cft_params, region):
    print('Verify CFT using Dome9 Compliance Engine')
    print("BundleId=%s" % bundle_id)
    # print("CFT=%s" % template)

    risk = 0

    params = convert_parameters_to_dome9_format(cft_params)
    print('using CFT parameters:%s' % params)
    request_id = uuid.uuid4()

    d9_region = region.replace("-", "_")

    # "CloudAccountId": d9_id, -   No need to use cloud account on the static cft analysis
    d9_request_data = {
        "id": bundle_id,
        "region": d9_region,
        "cft": {
            "rootName": "cft.json",
            "params": params,
            "files": [
                {"name": "cft.json", "template": template}
            ]
        },
        "isCft": True
        ,"requestId": str(request_id)
    }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    #print(d9_request_data)

    try:
        response = requests.post('https://api.dome9.com/v2/assessment/bundleV2', data=json.dumps(d9_request_data),
                                 headers=headers, auth=(d9_key, d9_secret))
        response.raise_for_status()
        # print(response.text)

        d9resp = json.loads(response.text)

    except Exception as e:
        raise Exception("Error - Dome9  API request_id: {}\n Error message: {}".format(request_id, e))

    # print(response.text)
    if 'errorMessage' in d9resp.keys():  # Evaluation error
        print('* Error during CFT evaluation: %s' % d9resp['errorMessage'])
        raise Exception(d9resp['errorMessage'])

    failed_rules = [json.dumps({
        'name': test['rule']['name'],
        'description': test['rule']['description'],
        'severity': test['rule']['severity'],
        'tag': test['rule']['complianceTag']
    }) for test in d9resp['tests'] if not test['testPassed']]

    # todo - we can develop some other heuristics based on risk to decide if to pass the test or not
    if len(failed_rules) > 0:
        risk = 100
        print('*** Found failed rules ***')
        # print("*** Risk is %d ***" %risk)
        print(failed_rules)
    else:
        print('CFT Test passed. No failed rules :)')

    url = "https://secure.dome9.com/v2/compliance-engine/result/%s" % d9resp['id']

    return risk, failed_rules, url


def convert_parameters_to_dome9_format(params_str):
    """convert a json string into a list of {key, value}
    See an example for input format in my-app-cft/prod-stack-configuration.json
    """
    try:
        params = json.loads(params_str)['Parameters']
        # TODO: handle Attribute excpetions here
        return [{'key': key, 'value': params[key]} for key in params]
    except:
        print('Could not parse the parameter:%s' % params_str)
        raise
