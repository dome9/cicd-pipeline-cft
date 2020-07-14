import os
path = os.getcwd()
os.chdir(path)

import logging
import argparse

import d9_sync_and_wait as d9_sync_and_wait
import d9_run_assessment as d9_run_assessment


APIVersion = 2.0

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


def print_help():
    title = '''


  ______  __        ______    __    __   _______   _______  __    __       ___      .______     _______           _______   ______   .___  ___.  _______   ___              
 /      ||  |      /  __  \  |  |  |  | |       \ /  _____||  |  |  |     /   \     |   _  \   |       \         |       \ /  __  \  |   \/   | |   ____| / _ \             
|  ,----'|  |     |  |  |  | |  |  |  | |  .--.  |  |  __  |  |  |  |    /  ^  \    |  |_)  |  |  .--.  |        |  .--.  |  |  |  | |  \  /  | |  |__   | (_) |      
|  |     |  |     |  |  |  | |  |  |  | |  |  |  |  | |_ | |  |  |  |   /  /_\  \   |      /   |  |  |  |        |  |  |  |  |  |  | |  |\/|  | |   __|   \__, |    
|  `----.|  `----.|  `--'  | |  `--'  | |  '--'  |  |__| | |  `--'  |  /  _____  \  |  |\  \-. |  '--'  |        |  '--'  |  `--'  | |  |  |  | |  |____    / /             
 \______||_______| \______/   \______/  |_______/ \______|  \______/  /__/     \__\ | _| `.__| |_______/         |_______/ \______/  |__|  |__| |_______|  /_/      
         
                    ____ _  _ _  _    ____ ____ ____ ____ ____ ____ _  _ ____ _  _ ___    ____ _  _ _    _       ___  _ ___  ____ _    _ _  _ ____
                    |__/ |  | |\ |    |__| [__  [__  |___ [__  [__  |\/| |___ |\ |  |     |___ |  | |    |       |__] | |__] |___ |    | |\ | |___
                    |  \ |__| | \|    |  | ___] ___] |___ ___] ___] |  | |___ | \|  |     |    |__| |___ |___    |    | |    |___ |___ | | \| |___
                                                                                                                                      

'''

    text = (
        f'Script Version - {APIVersion} \n\n'
        'This is the Dome9 JIT full assessment execution script \n'
        'The script flow - '
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


def main():
    parser = argparse.ArgumentParser(description='', usage=print_help())
    parser.add_argument('--d9keyId', required=True, type=str, help='the Dome9 KeyId for executing API calls')
    parser.add_argument('--d9secret', required=True, type=str, help='the Dome9 secret  for executing API calls')
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
    __log_setup(log_file_path=args.log_file_path, log_level=args.log_level)

    d9_sync_and_wait.run(args=args)
    d9_run_assessment.run(args=args)


if __name__ == "__main__":
    main()


