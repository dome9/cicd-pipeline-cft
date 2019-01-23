import requests
from requests.auth import HTTPBasicAuth
import json


def evaluate_cft_template(d9_key, d9_secret, bundle_id, template, cft_params, aws_account):
    print('Verify CFT using Dome9 Compliance Engine')
    print("BundleId=%s" % bundle_id)
    # print("CFT=%s" % template)
    global d9_id

    # Retrieving the dome9 account id
    if aws_account == "":
        print('* Error during CFT evaluation aws account parameter doesnt exist')
        raise Exception('AWS Account parameter does not exist ')

    else:
        r = requests.get('https://api.dome9.com/v2/cloudaccounts/{}'.format(aws_account),
                         auth=(d9_key, d9_secret))
        d9_id = r.json()['id']
        print('Found it. Dome9 cloud account Id={}'.format(d9_id))


    risk = 0

    params = convert_parameters_to_dome9_format(cft_params)
    print('using CFT parameters:%s' % params)


    d9_request_data = {
        "CloudAccountId": d9_id,
        "id": bundle_id,
        "region": "us_east_1",
        "cft": {
            "rootName": "cft.json",
            "params": params,
            "files": [
                {"name": "cft.json", "template": template}
            ]
        },
        "isCft":True
    }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # print(d9_request_data)

    response = requests.post('https://api.dome9.com/v2/assessment/bundleV2', data=json.dumps(d9_request_data),
                             headers=headers, auth=(d9_key, d9_secret))

    response.raise_for_status()

    # print(response.text)

    d9resp = json.loads(response.text)
    # print(response.text)
    if 'errorMessage' in d9resp.keys():  # Evaluation error
        print('* Error during CFT evaluation: %s' % d9resp['errorMessage'])
        raise Exception(d9resp['errorMessage'])

    failed_rules = [{
        'name': test['rule']['name'],
        'description': test['rule']['description'],
        'severity': test['rule']['severity'],
        'tag': test['rule']['complianceTag']
    } for test in d9resp['tests'] if not test['testPassed']]

    if len(failed_rules) > 0:
        severities = set()
        for test in failed_rules:
            severities.add(test['severity'])

        if "High" in severities:
            risk = 100
        else:
            if "Medium" in severities:
                risk = 50
            else:
                risk = 20


        print('*** Found failed rules ***')
        print("*** Risk is %d ***" %risk)
        print(failed_rules)
    else:
        print('CFT Test passed. No failed rules :)')
    url = "https://secure.dome9.com/v2/compliance-engine/result/%s" % d9resp['id']

    failed_rules = [json.dumps(test) for test in failed_rules]

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
