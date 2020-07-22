import os
path = os.getcwd()
os.chdir(path)

import sys
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
        if hasattr(obj,'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)

def __log_setup( log_level='INFO'):
    """
    setup the logger
    INFO - will go to stdout
    WARNING,ERROR AND DEBUG - will go to stderr
    :param log_level: the level of the log
    :return:
    """

    h1 = logging.StreamHandler(sys.stdout)
    formater = logging.Formatter('[%(asctime)s -%(levelname)s] (%(processName)-10s) %(message)s')
    h2 = logging.StreamHandler(sys.stderr)
    h3 = logging.StreamHandler(sys.stderr)
    h4 = logging.StreamHandler(sys.stderr)
    h1.setLevel(logging.INFO)
    h1.setFormatter(formater)
    h2.setLevel(logging.DEBUG)
    h2.addFilter(InfoFilter())
    h2.setFormatter(formater)
    h3.setLevel(logging.ERROR)
    h3.setFormatter(formater)
    h4.setLevel(logging.WARNING)
    h4.setFormatter(formater)



    logger = logging.getLogger()
    logger.addHandler(h1)
    logger.addHandler(h2)
    logger.addHandler(h3)
    logger.addHandler(h4)
    logger.setLevel(log_level)


def print_help():
    title = '''


  ______  __        ______    __    __   _______   _______  __    __       ___      .______     _______           _______   ______   .___  ___.  _______   ___              
 /      ||  |      /  __  \  |  |  |  | |       \ /  _____||  |  |  |     /   \     |   _  \   |       \         |       \ /  __  \  |   \/   | |   ____| / _ \             
|  ,----'|  |     |  |  |  | |  |  |  | |  .--.  |  |  __  |  |  |  |    /  ^  \    |  |_)  |  |  .--.  |        |  .--.  |  |  |  | |  \  /  | |  |__   | (_) |      
|  |     |  |     |  |  |  | |  |  |  | |  |  |  |  | |_ | |  |  |  |   /  /_\  \   |      /   |  |  |  |        |  |  |  |  |  |  | |  |\/|  | |   __|   \__, |    
|  `----.|  `----.|  `--'  | |  `--'  | |  '--'  |  |__| | |  `--'  |  /  _____  \  |  |\  \-. |  '--'  |        |  '--'  |  `--'  | |  |  |  | |  |____    / /             
 \______||_______| \______/   \______/  |_______/ \______|  \______/  /__/     \__\ | _| `.__| |_______/         |_______/ \______/  |__|  |__| |_______|  /_/      
         

             _   _  ___     __  ____ ____  ___ ____ ____ _  _  ___ _  _ ___     ___ _  _  ___  ___ _  _ ___ _ ____ _  _    ___  _     __  ___   ___
             |   |   |     |__| [__  [__  |___ [__  [__  |\/| |___ |\ |  |     |___  \/  |___ |    |  |  |  | |  | |\ |    |__] |    |__| |  \ |___
           |_|   |   |     |  | ___] ___] |___ ___] ___] |  | |___ | \|  |     |___ _/\_ |___ |___ |__|  |  | |__| | \|    |__] |___ |  | |__/ |___
                                                                                                                            
'''

    text = (
        f'Script Version - {APIVersion} \n\n'
        'This is the Dome9 JIT full assessment execution script \n'
        'The script flow - \n'
        '\t 1. Sync and wait - Fetching all the dome9 entities into dome9 env - Using d9_sync_and_wait.py\n'
        '\t 2. Execute the specific bundle - Using d9_run_assessment.py\n'
        'The script have two mode of operations:\n'
        '\t\t1. Execute it over specific cloud account  \n'
        '\t\t2. Execute it for a specific AWS Stack\n\n'
    )

    print(title)
    print(
        '\n-------------------------------------------------------------------------------------------------------------------------------------------------------')
    print(text)


def run(args):
    sl_result_file = os.environ["SHIFTLEFT_RESULT_FILE"]
    d9_sync_and_wait.run(args=args)
    tests_list = d9_run_assessment.run(args=args)

    # In case that minimal severity level was reached
    execution_status = 0
    if args.minimumSeverityForFail:
        if any(test.rule_severity == args.minimumSeverityForFail for test in tests_list):
            logging.info("Assessment was failed!!")
            logging.info(f"Minimal Severity level - {args.minimumSeverityForFail} was reached")
            execution_status = 2

    # Print result into the result file
    result_as_json = json.dumps([obj.reprJSON() for obj in tests_list])
    with open(sl_result_file, 'w') as file:
        file.write(result_as_json)

    exit(execution_status)

def main():
    d9_key_id = os.environ["CHKP_CLOUDGARD_ID"]
    d9_secret = os.environ["CHKP_CLOUDGUARD_SECRET"]
    sl_debug = os.environ["SHIFTLEFT_DEBUG"]

    parser = argparse.ArgumentParser(description='', usage=print_help())
    parser.add_argument('--d9keyId', required=False, default=d9_key_id, type=str, help='[the Dome9 KeyId for executing API calls - Can delivered by env vriable as well - CHKP_CLOUDGARD_ID]')
    parser.add_argument('--d9secret', required=False, default=d9_secret, type=str, help='[the Dome9 secret  for executing API calls - Can delivered by env vriable as well - CHKP_CLOUDGUARD_SECRET]')
    parser.add_argument('--awsCliProfile', required=False, type=str, default=None,
                        help='[the AWS profile of the AWS account that the stack was deployed to]')
    parser.add_argument('--awsAccountNumber', required=False, type=str, default=None,
                        help='[the AWS account to run the assessment on]')
    parser.add_argument('--cloudAccountD9Id', required=False, type=str, default=None,
                        help='[the d9 id of the cloud account to run the assessment on (can be taken form the d9 console)]')
    parser.add_argument('--region', required=False, type=str, default=None,
                        help='[the region where the stack was deployed to]')
    parser.add_argument('--stackName', required=False, type=str, default=None,
                        help='[the AWS stack name to assess]')
    parser.add_argument('--excludedTypes', required=False, type=str,
                        help='[which d9 the system should not wait till their d9 sync will finish]')
    parser.add_argument('--bundleId', required=True, type=int,
                        help='the dome9 bundle id to execute')
    parser.add_argument('--minimumSeverityForFail', required=False, type=str, default=None,
                        help='[the minimal severity level that will cause fail - Dome9 rule severity (High/Medium/Low)] ')
    parser.add_argument('--maxTimeoutMinutes', required=False, type=int, default=10,
                        help='[the maximum time to wait to sync to finish]')
    parser.add_argument('--log_file_path', required=False, type=str, default=None,
                        help='[the destination path of for the log]')
    parser.add_argument('--log_level', required=False, type=str, default='INFO',
                        help='[the execution level of the log]')

    args = parser.parse_args()



    log_level = args.log_level
    if sl_debug:
        log_level = 'DEBUG'

    __log_setup(log_level=log_level)

    run(args=args)



if __name__ == "__main__":
    main()


