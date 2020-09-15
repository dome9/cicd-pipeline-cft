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
import os
import logging
from sys import exit


APIVersion=2.0
SCRIPT='SyncAndWait'


def __d9_sync_and_wait(d9_api_key_Id, d9_api_secret, cloud_account_number, region, excluded_types, max_timeout_minutes=10):
    """
    This function will execute the d9 sync and will wait till it will finish
    :param d9_api_key_Id: d9 API keyid
    :param d9_api_secret: d9 API secret
    :param cloud_account_number: the AWS account number to run the sync on
    :param region: the region to sync
    :param excluded_types: the d9 type that we can ignore and not wait for them
    :param max_timeout_minutes: the maximun time to wait for each d9 type sync
    :return:
    """

    # Take start time
    t0_sync_wait = datetime.datetime.utcnow()
    logging.info("{} - CloudGuard Sync And Wait  Interface Version - {}".format(SCRIPT,APIVersion))
    logging.info("{} - Starting - Setting now (UTC {}) as base time".format(SCRIPT, t0_sync_wait))
    logging.info("{} - Max time for this execution is - {} minutes".format(SCRIPT,max_timeout_minutes ))


    if relevant_dome9_types:
        print_list(relevant_dome9_types, "Actual CloudGuard types to wait for")
    if excluded_types:
        print_list(excluded_types, "Excluded CloudGuard types (will not wait for their fetch status)")

    result = None
    #if awsAccNumber:
    #    # replace awsaccount number with Dome9 cloud account Id
    #    logging.info(f'resolving Dome9 account id from aws account number: {awsAccNumber}')
    #    r = requests.get('https://api.dome9.com/v2/cloudaccounts/{}'.format(awsAccNumber), auth=(d9keyId, d9secret))
    #    d9Id = r.json()['id']
    #    logging.info(f'Found it. Dome9 cloud account Id={d9Id}')

    # Perform SyncNow
    __perfrom_sync_now(cloud_account_number=cloud_account_number, d9_api_keyId=d9_api_key_Id, d9_api_secret=d9_api_secret)
    # time.sleep(5) # (optional) wait a few seconds to let the system opportunity to fetch entities

    # Params for holding state in case of exception we want them to be dump to the stdout
    num_of_completed = 0
    api_status = {}

    # Query Fetch status api, loop until ready
    while True:
        # First check that max timeout was not reached
        if __check_that_max_time_was_not_reached(t0_sync_wait, max_timeout_minutes):
            break

        curr_api_status = __query_fetch_status(cloud_account_id=cloud_account_number, region=region,
                                               relevant_dome9_types=relevant_dome9_types,
                                               d9_api_keyId=d9_api_key_Id, d9_api_secret=d9_api_secret,
                                               excluded_types=excluded_types)

        if __check_that_max_time_was_not_reached(t0_sync_wait, max_timeout_minutes):
            break

        result = __analyze_entities_update_status(relevant_dome9_types, curr_api_status, t0_sync_wait)

        curr_num_of_completed = result.getNumberofCompleted()

        # Case that the number of completed fetch was reduced from some reason
        if curr_num_of_completed < num_of_completed:
            logging.warning('{} - Stopping script, num of completed fetch was reduced,\n was - {} and now it is - {}'
                            .format(SCRIPT, num_of_completed, curr_num_of_completed))
            logging.warning('{} - Dump of the CloudGuard fetch status difference: '.format(SCRIPT))
            logging.warning('{} - Fetch start time - {}'.format(SCRIPT, t0_sync_wait))
            logging.warning('{} - Previous Status: '.format(SCRIPT))
            logging.warning('{} - {}'.format(SCRIPT, json.dumps(api_status, indent=4, sort_keys=True)))
            logging.warning('{} - Current Status - '.format(SCRIPT))
            logging.warning('{} - {}'.format(SCRIPT, json.dumps(curr_api_status, indent=4, sort_keys=True)))
            break

        num_of_completed = curr_num_of_completed
        api_status = curr_api_status

        #result.print_me()
        logging.info('{} - Completed: ({}), Pending: {}'.format(SCRIPT, len(result.completed), len(result.pending)))

        if (result.isAllCompleted()):
            break
        else:
            logging.debug('{} - Not done yet. Will sleep a bit and poll the status again...'.format(SCRIPT))
            time.sleep(30)



    # transform and return data set
    #result.nonSupportedCFTTypes = d9_non_supported_cfn
    return result

def __check_that_max_time_was_not_reached (t0_sync_wait, max_timeout_minutes):
    """
    This function checking if the time out was reached
    :param t0_sync_wait: the time where the sync started
    :param max_timeout_minutes: the configured timeout value
    :return:
    """
    t_now = datetime.datetime.utcnow()
    elapsed = (t_now - t0_sync_wait).total_seconds()
    logging.debug('{} - Current d9_sync_and_wait run time is  - {} Seconds'.format(SCRIPT, elapsed))
    if elapsed > max_timeout_minutes * 60:
        logging.error('{} - Stopping script, passed maxTimeoutMinutes ({})'.format(SCRIPT, max_timeout_minutes))
        return True
    return False

def __analyze_entities_update_status(relevant_dome9_types, api_status, t0_sync_wait):
    """
    This function anlyzing the reponse of EntityFetchStatus in Dome9 API and return the StatusResult object
    :param relevant_dome9_types: (optional) the relevant types that d9 support
    :param api_status: the result of the execution of - Dome9 API - GET /v2/EntityFetchStatus
    :param t0_sync_wait: the start time of the sync
    :return: StatusResult
    """

    retObj = StatusResult()

    if relevant_dome9_types:
        for d9_type in relevant_dome9_types:
            filteredList = [elem for elem in api_status if elem[
                'entityType'] == d9_type]  # There should be either 1 or 0 items here (as we already filtered the regions)
            ser_status = next(iter(filteredList), None)  # get first item or nothing
            if (not ser_status):
                retObj.pending.append(
                    d9_type)  # if for some reason the desired type is not in our DB - treat it as pending. Hopefully it'll be added soon. If not - there might be a bug in our mapping file, meaning no such Dome9 type exists.
            else:
                # sadly datetime.datetime.utcnow() is not timzeone aware so I'm removing the TZ so we can compare them
                tEntity = dateutil.parser.parse(ser_status['lastSuccessfulRun']).replace(tzinfo=None)
                if tEntity > t0_sync_wait:
                    retObj.completed.append(d9_type)
                else:
                    retObj.pending.append(d9_type)
    else:
        for entry in api_status:
            # sadly datetime.datetime.utcnow() is not timzeone aware so I'm removing the TZ so we can compare them
            tEntity = dateutil.parser.parse(entry['lastSuccessfulRun']).replace(tzinfo=None)
            if tEntity > t0_sync_wait:
                retObj.completed.append(entry['entityType'])
            else:
                retObj.pending.append(entry['entityType'])

    return retObj

def __perfrom_sync_now(cloud_account_number, d9_api_keyId, d9_api_secret):
    """
    The function that will perform Dome9 sync API call
    :param cloud_account_number: The cloud account to sync
    :param d9_api_keyId: Dome9 API key
    :param d9_api_secret: Dome9 API secret
    :return:
    """

    # now perform sync now
    logging.debug('{} - Sending CloudGuard SyncNow command...'.format(SCRIPT))
    try:
        headers = {
            'Accept': 'application/json'
        }
        r = requests.post('https://api.dome9.com/v2/cloudaccounts/{}/SyncNow'.format(cloud_account_number),params={},
                          headers=headers, auth=(d9_api_keyId, d9_api_secret))
        r.raise_for_status()  # throw an error if we did not get an OK result
        resp = r.json()
        logging.debug('{} - {}'.format(SCRIPT, resp))
    except Exception as e:
        logging.error('{} - CloudGuard sync API call failed: {}'.format(SCRIPT, e))
    return

def __query_fetch_status(cloud_account_id, relevant_dome9_types, d9_api_keyId, d9_api_secret, excluded_types, region=None):
    """
    This function checking the status of the d9 fetching (sync)
    :param cloud_account_id: The cloud account to sync
    :param relevant_dome9_types: (optional) the relevant types supported by d9 sync
    :param d9_api_keyId:  Dome9 API key
    :param d9_api_secret: Dome9 API secret
    :param d9_api_secret: Dome9 API secret
    :param excluded_types: list of types that are no supported in dome9 sync now api
    :return:
    """
    logging.debug('{} - Querying entities fetch status from Dome9 API...'.format(SCRIPT))
    try:
        r = requests.get('https://api.dome9.com/v2/EntityFetchStatus?cloudAccountId={}'.format(cloud_account_id),
                         auth=(d9_api_keyId, d9_api_secret))
        #r = requests.get('https://api.dome9.com/v2/EntityFetchStatus?externalAccountNumber={}'.format(awsAccNumber),
        #                 auth=(d9keyId, d9secret))
        resp = r.json()
        if region:
            d9region = region.replace('-', '_')  # dome9 identifies regions with underscores
            relevant = list(filter(lambda entry: entry['region'] in [d9region, ''],
                              filter(lambda entry: entry['entityType'] in relevant_dome9_types if relevant_dome9_types else entry['entityType'] not in excluded_types,
                                     resp)))
        else:
            relevant = list(filter(lambda entry: entry['entityType'] in relevant_dome9_types if relevant_dome9_types else entry['entityType'] not in excluded_types,resp))

        return relevant
    except Exception as e:
        logging.error("{} - Query d9 fetch status failed: {}".format(SCRIPT,e))

def __get_relevant_types(aws_acc_number, region, stack_name, excluded_types, aws_profile, candidate_types_to_wait=None):
    """
    In case of execution oriented to a specific stack  query the AWS account about the stack assets
    otherwise just keep the relevant types that dome9 support for sync now API
    :param aws_acc_number: the aws account where the stack was deployed to
    :param region: the region where the task deployed to
    :param stack_name: the name of the stack
    :param excluded_types: the types we want to ignore
    :param aws_profile: the aws profile to use for query the aws account
    :return: (d9_supported_cfn_types, d9_non_supported_cfn,actual_d9_types) -
        d9_supported_cfn_types - the d9  cloud formation supported types
        d9_non_supported_cfn - the non supported cloud formation types in d9
        actual_d9_types - the relevant types as represented in d9
    """
    d9_supported_cfn_types=[]
    d9_non_supported_cfn=[]
    if stack_name:
        # query AWS for relevant stack types
        relevant_cfn_types = __get_stack_types_from_aws(aws_acc_number, region, stack_name, aws_profile)
        print_list(relevant_cfn_types, 'CFN types found in this stack')

        # get dome9 types from mapping file
        MAPPINGS_PATH = "%s/cfn_mappings.csv" % (os.path.dirname(os.path.realpath(__file__)))
        cfn_mappings = dict()
        with open(MAPPINGS_PATH, "r") as f:
            reader = csv.DictReader(f)
            for item in reader:
                if item['Dome9']:
                    cfn_mappings[item['CFN']] = item['Dome9'].split(',')

        # the dome9 representation for each relevant type from the stack
        d9_supported_cfn_types = [cfn for cfn in relevant_cfn_types if cfn in cfn_mappings]
        print_list(d9_supported_cfn_types, "Relevant CFN types SUPPORTED by Dome9")

        d9_non_supported_cfn = [cfn for cfn in relevant_cfn_types if not cfn in cfn_mappings]
        print_list(d9_non_supported_cfn, "Relevant CFN types NOT supported by Dome9")

        relevant_dome9_types = set(
            flatten([cfn_mappings[cfn] if cfn in cfn_mappings else list([]) for cfn in relevant_cfn_types]))
        # print_list(relevant_dome9_types,'relevant Dome9 Data fetcher types')
        actual_d9_types = [t for t in relevant_dome9_types if not t in excluded_types]
    else:
        actual_d9_types = [t for t in candidate_types_to_wait if not t in excluded_types]




    return (d9_supported_cfn_types, d9_non_supported_cfn,actual_d9_types)

def __get_stack_types_from_aws(aws_acc_number, region, stack_name, aws_profile):
    """
    Use Boto to query AWS account about the assets and type of specific task
    :param aws_acc_number: the aws account where the stack was deployed to
    :param region: the region where the task deployed to
    :param stack_name: the name of the stack
    :param aws_profile: the aws profile to use for query the aws account
    :return:
    """
    # allow to specify specific profile, fallback to standard boto credentials lookup strategy https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
    aws_session = boto3.session.Session(profile_name=aws_profile,
                                        region_name=region) if aws_profile else boto3.session.Session(region_name=region)

    # sanity test - verify that we have credentials for the relevant AWS account numnber
    sts = aws_session.client('sts')
    account_id = sts.get_caller_identity()["Account"]
    if aws_acc_number != account_id:
        logging.error('{} - Error - the provided awsAccNumber ({}) is not tied to the AWS credentials of this script '
                      '({}) consider providing a different "profile" argument'.format(SCRIPT, aws_acc_number,
                                                                                      account_id))
        exit(1)

    cfn = aws_session.client('cloudformation')
    response_pages = list()
    api_response = cfn.list_stack_resources(StackName=stack_name)

    logging.debug("{}".format(api_response))
    response_pages.append(api_response)
    while 'NextToken' in api_response:
        api_response = cfn.list_stack_resources(
            StackName=stack_name,
            NextToken=api_response['NextToken']
        )
        response_pages.append(api_response)

    # set will make it unique
    relevant_cfn_types = list(
        set([resource['ResourceType'] for response in response_pages for resource in response['StackResourceSummaries']]))

    return relevant_cfn_types


# Utility methods

def print_list(list, name):
    if name:
        header = '{} ({}):'.format(name, len(list))
        logging.info("{} - {} {}".format(SCRIPT, header, ','.join(list)))



def flatten(l):
    return [item for sublist in l for item in sublist]


def print_help():
    title = '''
  ______  __        ______    __    __   _______   _______  __    __       ___      .______      _______      _______   ______   .___  ___.  _______   ___              
 /      ||  |      /  __  \  |  |  |  | |       \ /  _____||  |  |  |     /   \     |   _  \    |       \    |       \ /  __  \  |   \/   | |   ____| / _ \             
|  ,----'|  |     |  |  |  | |  |  |  | |  .--.  |  |  __  |  |  |  |    /  ^  \    |  |_)  |   |  .--.  |   |  .--.  |  |  |  | |  \  /  | |  |__   | (_) |      
|  |     |  |     |  |  |  | |  |  |  | |  |  |  |  | |_ | |  |  |  |   /  /_\  \   |      /    |  |  |  |   |  |  |  |  |  |  | |  |\/|  | |   __|   \__, |    
|  `----.|  `----.|  `--'  | |  `--'  | |  '--'  |  |__| | |  `--'  |  /  _____  \  |  |\  \-.  |  '--'  |   |  '--'  |  `--'  | |  |  |  | |  |____    / /             
 \______||_______| \______/   \______/  |_______/ \______|  \______/  /__/     \__\ | _| `.__|  |_______/    |_______/ \______/  |__|  |__| |_______|  /_/              
                                                                                                                                                                         
                                                 ____ _   _ _  _ ____    ____ _  _ ___     _ _ _ ____ _ ___
                                                [__   \_/  |\ | |       |__| |\ | |  \    | | | |__| |  | 
                                                ___]   |   | \| |___    |  | | \| |__/    |_|_| |  | |  | 
                                                                                                                                                
                                                                                                                                                                         
  '''



    text = ('Script Version - {} \n\n'
            'This is the sync and wait script \n'
            'It will trigger data fetch for specific cloud account secured by Dome9 system \n'
            'This is the first step before executing remote assessment  \n'
            'The script have two mode of operations:\n'
            '\t\t1. Execute it across the entire cloud account \n'
            '\t\t2. Execute it for a specific AWS Stack\n\n'.format(APIVersion)
          )

    print(title)
    print('\n------------------------------------------------------------------')
    print(text)


def __log_setup(log_file_path=None, log_level='INFO'):
    """
    setup the logging level
    :param log_file_psth: the destination log file path
    :param log_level: the level of the log
    :return:
    """

    if log_file_path:
        logging.basicConfig(filename=log_file_path,
                            format='[%(asctime)s -%(levelname)s] (%(processName)-10s) %(message)s')
    else:
        logging.basicConfig(format='[%(asctime)s -%(levelname)s] (%(processName)-10s) %(message)s')
    logging.getLogger().setLevel(log_level)

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


def run(args):
    global relevant_dome9_types
    # TODO - EXTEND THE DEFAULT LIST BY THE DOME9 UNSUPPORTED SYNC AND WAIT ENTITIES
    excluded_types = args.excluded_types.split(',') if args.excluded_types else ['LogGroups', 'IamCredentialReport','ConfigurationRecorder','DirectConnectVirtualInterface','EbsSnapshot', 'DirectConnectConnection', 'IamAccountSummary','GlueSecurityConfiguration']
    # In case of running assessment refer to a specific stack
    relevant_dome9_types = None
    if 'aws_cli_profile' in args:
        aws_profile = args.aws_cli_profile
    else:
        aws_profile = None

    if args.stack_name is not None:
        (d9_supported_cfn_types, d9_non_supported_cfn, relevant_dome9_types) = __get_relevant_types(
            args.aws_account_number,
            args.region,
            args.stack_name,
            excluded_types,
            aws_profile
            )
    t1 = datetime.datetime.utcnow()
    result = __d9_sync_and_wait(cloud_account_number=args.cloud_guard_account_id, region=args.region,
                            excluded_types=excluded_types, max_timeout_minutes=args.max_timeout_in_minutes,
                            d9_api_key_Id=args.cp_cloud_guard_id, d9_api_secret=args.cp_cloud_guard_secret)
    t2 = datetime.datetime.utcnow()
    total_sec = (t2 - t1).total_seconds()
    logging.info("{} - Run Sync And Wait Script ran for {} seconds".format(SCRIPT, total_sec))
    if (result.isAllCompleted()):
        logging.info("{} - All supported services were successfully updated (fetched)".format(SCRIPT))
        return True
    else:
        logging.error(
            "{} -not all types were updated. Please consider to increase the script timeout or to exclude \n these "
            "types from being wait upon: {}".format(SCRIPT, ",".join(set(result.pending))))
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='', usage=print_help())
    parser.add_argument('--d9keyId', required=True, type=str, help='the Dome9 KeyId for executing API calls')
    parser.add_argument('--d9secret', required=True, type=str, help='the Dome9 secret  for executing API calls')
    parser.add_argument('--cloudAccountD9Id', required=True, type=str,
                        help='the d9 id of the cloud account to run the sync on (can be taken form the d9 console)')
    parser.add_argument('--awsAccountNumber', required=False, type=str,  default=None,
                        help='[the AWS account to run the sync on]')
    parser.add_argument('--awsCliProfile', required=False, type=str,
                        help='[the AWS profile of the AWS account that the stack was deployed to]')
    parser.add_argument('--region', required=False, type=str,  default=None,
                        help='[the region where the stack was deployed to]')
    parser.add_argument('--stackName', required=False, type=str,  default=None,
                        help='[the AWS stack name to assess]')
    parser.add_argument('--excludedTypes', required=False, type=str,
                        help='[which d9 the system should not wait till their d9 sync will finish]')
    parser.add_argument('--maxTimeoutMinutes', required=False, type=int, default=10,
                        help='[the maximum time to wait to sync to finish]')
    parser.add_argument('--log_file_path', required=False, type=str, default=None,
                        help='[the destination path of for the log]')
    parser.add_argument('--log_level', required=False, type=str, default='INFO',
                        help='[the execution level of the log]')
    parser.add_argument('--isStandAlone', required=False, type=bool, default=False,
                        help='[Flag if this sync and wait execution is stand alone (not part of the all JIT '
                             'assessment execution)]')
    args = parser.parse_args()

    __log_setup(log_file_path=args.log_file_path, log_level=args.log_level)

    res = run(args)

    if args.isStandAlone:
        exit(0)


# TODO 1 allow 2nd run without triggering a sync now and with accepting the previous time as base time.

