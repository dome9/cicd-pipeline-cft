# 3rd party libraries
import boto3  # $ pip install boto3
import requests  # $ pip install requests

# python standard libraries
import csv
import datetime
import json
import time
import dateutil.parser
import argparse


def d9_sync_and_wait(d9keyId, d9secret, awsAccNumber, region, stackName, excludedTypes, maxTimeoutMinutes=10,
                     awsprofile=''):
    # Take start time
    t0 = datetime.datetime.utcnow()
    print("\n\n{}\nStarting...\n{}\n\nSetting now (UTC {}) as base time".format(80 * '*', 80 * '*', t0))
    (d9_supported_cfn_types, d9_non_supported_cfn, relevant_dome9_types) = get_relevant_stack_types(awsAccNumber,
                                                                                                    region, stackName,
                                                                                                    excludedTypes,
                                                                                                    awsprofile)

    # Perform SyncNow
    perfrom_sync_now(awsAccNumber, d9keyId, d9secret)
    # time.sleep(5) # (optional) wait a few seconds to let the system opportunity to fetch entities

    # Params for holding state in case of exception we want them to be dump to the stdout
    num_of_completed = 0
    api_status = {}


    # Query Fetch status api, loop until ready
    while True:
        curr_api_status = query_fetch_status(awsAccNumber, region, relevant_dome9_types, d9keyId, d9secret)
        result = analyze_entities_update_status(relevant_dome9_types, curr_api_status, t0)


        curr_num_of_completed = result.getNumberofCompleted()


        # Case that the number of completed fetch was reduced from some reason
        if curr_num_of_completed < num_of_completed:
            print('Stopping script, num of completed fetch was reduced, was - {} and now it is - {}'.format(
                num_of_completed, curr_num_of_completed))
            print('Dump of the Dome9 fetch status difference - ')
            print('Fetch start time - {}'.format(t0))
            print('Previous Status - ')
            print(json.dumps(api_status, indent=4, sort_keys=True))
            print('')
            print('Current Status - ')
            print(json.dumps(curr_api_status, indent=4, sort_keys=True))
            print('')
            break

        num_of_completed = curr_num_of_completed
        api_status = curr_api_status

        result.print_me()
        if (result.isAllCompleted()):
            break
        tNow = datetime.datetime.utcnow()
        elapsed = (tNow - t0).total_seconds()
        if elapsed > maxTimeoutMinutes * 60:
            print('\nStopping script, passed maxTimeoutMinutes ({})'.format(maxTimeoutMinutes))
            break
        else:
            print('\nNot done yet. Will sleep a bit and poll the status again...')
            time.sleep(30)



    # transform and return data set
    result.nonSupportedCFTTypes = d9_non_supported_cfn
    return result


def analyze_entities_update_status(relevant_dome9_types, api_status, t0):
    retObj = StatusResult()
    for d9type in relevant_dome9_types:
        filteredList = [elem for elem in api_status if elem[
            'entityType'] == d9type]  # There should be either 1 or 0 items here (as we already filtered the regions)
        ser_status = next(iter(filteredList), None)  # get first item or nothing
        if (not ser_status):
            retObj.pending.append(
                d9type)  # if for some reason the desired type is not in our DB - treat it as pending. Hopefully it'll be added soon. If not - there might be a bug in our mapping file, meaning no such Dome9 type exists.
        else:
            tEntity = dateutil.parser.parse(ser_status['lastSuccessfulRun']).replace(
                tzinfo=None)  # sadly datetime.datetime.utcnow() is not timzeone aware so I'm removing the TZ so we can compare them
            if tEntity > t0:
                retObj.completed.append(d9type)
            else:
                retObj.pending.append(d9type)

    return retObj


def perfrom_sync_now(awsAccNumber, d9keyId, d9secret):
    # replace awsaccount number with Dome9 cloud account Id
    print('\nresolving Dome9 account id from aws account number: {}'.format(awsAccNumber))
    r = requests.get('https://api.dome9.com/v2/cloudaccounts/{}'.format(awsAccNumber), auth=(d9keyId, d9secret))

    d9Id = r.json()['id']
    print('Found it. Dome9 cloud account Id={}'.format(d9Id))

    # now perform sync now
    print('\nSending Dome9 SyncNow command...')
    r = requests.post('https://api.dome9.com/v2/cloudaccounts/{}/SyncNow'.format(d9Id), auth=(d9keyId, d9secret))
    r.raise_for_status()  # throw an error if we did not get an OK result
    resp = r.json()
    print(resp)

    return


def query_fetch_status(awsAccNumber, region, relevant_dome9_types, d9keyId, d9secret):
    print('Querying entities fetch status from Dome9 API...')
    r = requests.get('https://api.dome9.com/v2/EntityFetchStatus?externalAccountNumber={}'.format(awsAccNumber),
                     auth=(d9keyId, d9secret))
    resp = r.json()
    d9region = region.replace('-', '_')  # dome9 identifies regions with underscores
    relevant = list(filter(lambda entry: entry['region'] in [d9region, ''],
                      filter(lambda entry: entry['entityType'] in relevant_dome9_types,
                             resp)))
    return relevant


def get_relevant_stack_types(awsAccNumber, region, stackName, excludedTypes, awsprofile):
    # query AWS for
    relevant_cfn_types = get_stack_types_from_aws(awsAccNumber, region, stackName, awsprofile)
    print_list(relevant_cfn_types, 'CFN types found in this stack')

    # get dome9 types from mapping file
    MAPPINGS_PATH = "./cfn_mappings.csv"
    cfn_mappings = dict()
    with open(MAPPINGS_PATH, "r") as f:
        reader = csv.DictReader(f)
        for item in reader:
            if item['Dome9']:
                cfn_mappings[item['CFN']] = item['Dome9'].split(',')

    d9_supported_cfn_types = [cfn for cfn in relevant_cfn_types if cfn in cfn_mappings]
    print_list(d9_supported_cfn_types, "Relevant CFN types SUPPORTED by Dome9")

    d9_non_supported_cfn = [cfn for cfn in relevant_cfn_types if not cfn in cfn_mappings]
    print_list(d9_non_supported_cfn, "Relevant CFN types NOT supported by Dome9")

    relevant_dome9_types = set(
        flatten([cfn_mappings[cfn] if cfn in cfn_mappings else list([]) for cfn in relevant_cfn_types]))
    # print_list(relevant_dome9_types,'relevant Dome9 Data fetcher types')

    actual_d9_types = [t for t in relevant_dome9_types if not t in excludedTypes]
    print_list(actual_d9_types, "Actual Dome9 types to wait for")
    print_list(excludedTypes, "Excluded Dome9 types (will not wait for their fetch status)")

    return (d9_supported_cfn_types, d9_non_supported_cfn,actual_d9_types)


def get_stack_types_from_aws(awsAccNumber, region, stackName, awsprofile):
    # allow to specify specific profile, fallback to standard boto credentials lookup strategy https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
    aws_session = boto3.session.Session(profile_name=awsprofile,
                                        region_name=region) if awsprofile else boto3.session.Session(region_name=region)

    # sanity test - verify that we have credentials for the relevant AWS account numnber
    sts = aws_session.client('sts')
    account_id = sts.get_caller_identity()["Account"]
    if (awsAccNumber != account_id):
        print(
            'Error - the provided awsAccNumber ({}) is not tied to the AWS credentials of this script ({}) consider providing a different "profile" argument'.format(
                awsAccNumber, account_id))
        exit(2)

    cfn = aws_session.client('cloudformation')
    response_pages = list()
    api_response = cfn.list_stack_resources(
        StackName=stackName,
    )

    # print(api_response)
    response_pages.append(api_response)
    while 'NextToken' in api_response:
        api_response = cfn.list_stack_resources(
            StackName=stackName,
            NextToken=api_response['NextToken']
        )
        response_pages.append(api_response)

    # set will make it unique
    relevant_cfn_types = list(
        set([i['ResourceType'] for response in response_pages for i in response['StackResourceSummaries']]))

    return relevant_cfn_types


# Utility methods

def print_list(list, name):
    if name:
        header = '{} ({}):'.format(name, len(list))
        print('\n{}\n{}'.format(header, len(header) * '-'))
    print('\n'.join(list))


def flatten(l):
    return [item for sublist in l for item in sublist]


class StatusResult:
    def __init__(self):
        self.completed = []
        self.pending = []

    def isAllCompleted(self):
        return len(self.pending) == 0

    def getNumberofCompleted(self):
        return len(self.completed)

    def print_me(self):
        print_list(self.completed, "Completed")
        print_list(self.pending, "Pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--d9keyId', required=True, type=str)
    parser.add_argument('--d9secret', required=True, type=str)
    parser.add_argument('--awsCliProfile', required=False, type=str)
    parser.add_argument('--awsAccountNumber', required=True, type=str)
    parser.add_argument('--region', required=True, type=str)
    parser.add_argument('--stackName', required=True, type=str)
    parser.add_argument('--excludedTypes', required=False, type=str)
    parser.add_argument('--maxTimeoutMinutes', required=False, type=int, default=10)
    args = parser.parse_args()
    excludedTypes = args.excludedTypes.split(
        ',') if args.excludedTypes else []  # these are types which are not yet supported by sync now and are not critical for our GSL rules. (ex: LogGroups is not even a GSL entity)
    t1 = datetime.datetime.utcnow()

    st = d9_sync_and_wait(awsAccNumber=args.awsAccountNumber, region=args.region, stackName=args.stackName,
                          excludedTypes=excludedTypes, maxTimeoutMinutes=args.maxTimeoutMinutes,
                          awsprofile=args.awsCliProfile, d9keyId=args.d9keyId, d9secret=args.d9secret)

    t2 = datetime.datetime.utcnow()
    print('Script ran for {} seconds'.format((t2 - t1).total_seconds()))
    if (st.isAllCompleted()):
        print("\n*** All supported services were successfully updated (fetched) ***\n")
        exit(0)
    else:
        print(
            'not all types were updated. Please consider to increase the script timeout or to exclude these types from being wait upon: {}'.format(
                ",".join(st.pending)))
        exit(1)

# TODO 1 allow 2nd run without triggering a sync now and with accepting the previous time as base time.

