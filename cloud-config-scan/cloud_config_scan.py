import os

path = os.getcwd()
os.chdir(path)

try:
    import configparser
except ImportError:
    import ConfigParser

import sys
from sys import exit
import logging
import argparse
import json

import d9_sync_and_wait as d9_sync_and_wait
import d9_run_assessment as d9_run_assessment

APIVersion = 2.0


class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.ERROR, logging.WARNING)


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)


def __log_setup(log_level='INFO'):
    """
    setup the logger
    INFO - will go to stdout
    WARNING,ERROR AND DEBUG - will go to stderr
    :param log_level: the level of the log
    :return:
    """

    if log_level == 'INFO':
        h = logging.StreamHandler(sys.stdout)
    else:
        h = logging.StreamHandler(sys.stderr)

    formater = logging.Formatter('[%(asctime)s -%(levelname)s] (%(processName)-10s) %(message)s')

    h.setFormatter(formater)
    h.setLevel(log_level)
    logger = logging.getLogger()
    logger.addHandler(h)
    logger.setLevel(log_level)


def print_help():
    title = '''


                          ______  __        ______    __    __   _______   _______  __    __       ___      .______     _______               
                         /      ||  |      /  __  \  |  |  |  | |       \ /  _____||  |  |  |     /   \     |   _  \   |       \              
                        |  ,----'|  |     |  |  |  | |  |  |  | |  .--.  |  |  __  |  |  |  |    /  ^  \    |  |_)  |  |  .--.  |       
                        |  |     |  |     |  |  |  | |  |  |  | |  |  |  |  | |_ | |  |  |  |   /  /_\  \   |      /   |  |  |  |     
                        |  `----.|  `----.|  `--'  | |  `--'  | |  '--'  |  |__| | |  `--'  |  /  _____  \  |  |\  \-. |  '--'  |             
                         \______||_______| \______/   \______/  |_______/ \______|  \______/  /__/     \__\ | _| `.__| |_______/      
         

             _   _  ___     __  ____ ____  ___ ____ ____ _  _  ___ _  _ ___     ___ _  _  ___  ___ _  _ ___ _ ____ _  _    ___  _     __  ___   ___
             |   |   |     |__| [__  [__  |___ [__  [__  |\/| |___ |\ |  |     |___  \/  |___ |    |  |  |  | |  | |\ |    |__] |    |__| |  \ |___
           |_|   |   |     |  | ___] ___] |___ ___] ___] |  | |___ | \|  |     |___ _/\_ |___ |___ |__|  |  | |__| | \|    |__] |___ |  | |__/ |___
                                                                                                                            
'''

    text = (
        'Script Version - {} \n\n'
        'This is the CloudGuard JIT full assessment execution blade \n'
        'The script flow - \n'
        '\t 1. Sync and wait - Fetching all the entities into CloudGuard enviornment\n'
        '\t 2. Execute the specific bundle\n'
        'The script has two mode of operations:\n'
        '\t\t1. Execute it over specific cloud account  \n'
        '\t\t\t\t ./shiftleft cloud_config_sca --cloud-guard-account-id <value> --bundle-id <value> --region <optional value>\n'
        '\t\t2. Execute it for a specific AWS Stack\n\n'
        '\t\t\t\t ./shiftleft cloud_config_sca --cloud-guard-account-id <value> --bundle-id <value> --stack-name <value> --region <value>\n\n'.format(APIVersion)
    )

    print(title)
    print(
        '\n-------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(text)

def print_map(failed_Test_relevant_entites_map):
    str = ""
    for test in failed_Test_relevant_entites_map:
        str += test.__str__()
    return str


def run(args):
    sl_result_file = os.environ["SHIFTLEFT_RESULT_FILE"]
    d9_sync_and_wait.run(args=args)
    logging.info('-'*50)
    tests_list = d9_run_assessment.run(args=args)

    # In case that minimal severity level was reached
    execution_status = 0

    if args.minimal_severity_for_fail:
        if any(test.rule_severity == args.minimal_severity_for_fail for test in tests_list):
            logging.info("Assessment was failed!!")
            print(print_map(tests_list))
            logging.info("Minimal Severity level - '{}' was reached".format(args.minimal_severity_for_fail))
            execution_status = 2

    # Print result into the result file
    result_as_json = json.dumps([obj.reprJSON() for obj in tests_list])
    with open(sl_result_file, 'w') as file:
        file.write(result_as_json)
    logging.info("Result can be found at - {}".format(sl_result_file))
    exit(execution_status)


def main():
    try:
        d9_key_id = os.environ["CHKP_CLOUDGARD_ID"]
    except KeyError as e:
        d9_key_id=''
    try:
        d9_secret = os.environ["CHKP_CLOUDGUARD_SECRET"]
    except  KeyError as e:
        d9_secret=''





    try:
        # take the shift left time out configuration and convert it to minutes and subtract one minute to enable
        # appropriate finish in case of fail
        time_out = int(int(os.environ["SHIFTLEFT_TIMEOUT"]) / 60) - 1
    except  KeyError as e:
        time_out = 10



    parser = argparse.ArgumentParser(description='', usage=print_help())
    parser.add_argument('--cp-cloud-guard-id', required=False, default=d9_key_id, type=str,
                        help='[the CloudGuard API Key - default is to use - CHKP_CLOUDGARD_ID env variable]')
    parser.add_argument('--cp-cloud-guard-secret', required=False, default=d9_secret, type=str,
                        help='[the CloudGuard secret  - default is to use - CHKP_CLOUDGUARD_SECRET env variable]')
    parser.add_argument('--aws-cli-profile', required=False, type=str, default=None,
                        help='[the AWS creds profile of the AWS account]')
    parser.add_argument('--aws-account-number', required=False, type=str, default=None,
                        help='[the AWS account to run the assessment on]')
    parser.add_argument('--cloud-guard-account-id', required=False, type=str, default=None,
                        help='[the CloudGuard id of the cloud account to run the assessment on (can be taken form the CloudGuard console)]')
    parser.add_argument('--region', required=False, type=str, default=None,
                        help='[the region where to run the assessment on]')
    parser.add_argument('--stack-name', required=False, type=str, default=None,
                        help='[the AWS stack name to assess]')
    parser.add_argument('--excluded-types', required=False, type=str,
                        help='[comma separated list of types which are excluded from the sync process.]')
    parser.add_argument('--bundle-id', required=True, type=int,
                        help='the CloudGuard bundle id to execute')
    parser.add_argument('--minimal-severity-for-fail', required=False, type=str, default="High",
                        help='[the minimal severity level that will cause fail - CloudGuard rule severity (High/Medium/Low), default is High] ')
    parser.add_argument('--max-timeout-in-minutes', required=False, type=int, default=time_out,
                        help='[the maximum time to wait for the script to run - default is to use - SHIFTLEFT_TIMEOUT env variable]')
    parser.add_argument('--log_file_path', required=False, type=str, default=None,
                        help='[the destination path of for the log]')

    args = parser.parse_args()

    sl_debug = os.environ["SHIFTLEFT_DEBUG"]

    log_level = 'INFO'
    if sl_debug.lower() == 'true':
        log_level = 'DEBUG'

    __log_setup(log_level=log_level)

    run(args=args)


if __name__ == "__main__":
    main()
