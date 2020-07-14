# 3rd party libraries
import boto3  # $ pip install boto3
import requests  # $ pip install requests

# python standard libraries
import json
import csv
import argparse
import datetime
import os
import logging

t0 = datetime.datetime.utcnow()
total_sec = 0
APIVersion = 2.0


class FailedEntity:
    def __init__(self):
        self.entity_id = None
        self.arn = None
        self.name = None
        self.tags = None
        self.type = None

    def set_entity_id(self, entity_id):
        self.entity_id = entity_id

    def set_arn(self, arn):
        self.arn = arn

    def set_name(self, name):
        self.name = name

    def set_tags(self, tags):
        self.tags = tags

    def set_type(self, type):
        self.type = type

    def __str__(self):
        rep = "\t\t\tEntity:\n"
        rep += ''.join(filter(None, ["\t\t\t\ttype: ", self.type, "\n"]))
        rep += ''.join(filter(None, ["\t\t\t\tname: ", self.name, "\n"]))
        rep += ''.join(filter(None, ["\t\t\t\tid: ", self.entity_id, "\n"]))
        # rep += ''.join(filter(None, ["\t\t\tarn: ", self.arn, "\n"]))

        return rep


class FailedTest:
    def __init__(self):
        self.rule_name = None
        self.rule_desc = None
        self.rule_severity = None

    def set_rule_name(self, rule_name):
        self.rule_name = rule_name

    def set_rule_desc(self, rule_desc):
        self.rule_desc = rule_desc

    def set_rule_severity(self, rule_severity):
        self.rule_severity = rule_severity

    def __str__(self):
        rep = "\n\tTest:\n"
        rep += "\t\trule name: " + self.rule_name + "\n"
        rep += "\t\tseverity: " + self.rule_severity + "\n"
        # rep += "\t\tdescription: " + self.rule_desc + "\n"

        return rep


def run_assessment(bundle_id, d9_secret, d9_key, region, d9_cloud_account=None, maxTimeoutMinutes=10):
    """
    This is the actual function that execute the assessment and gather the results
    :param bundle_id: dome9 bundle id to execute (according to version 1.0 should be taken from the Dome9 Console)
    :param d9_secret: Dome9 API secret
    :param d9_key:  Dome9 API key
    :param region: the region to run the assessment on
    :param d9_cloud_account:  the cloud account id as it represented at Dome9 system (should be taken from the console)
    :param maxTimeoutMinutes: the maximum time to wait for the execution to finish
    :return:
    """

    global t0, total_sec

    t0_run_assessment = datetime.datetime.utcnow()
    t0 = datetime.datetime.utcnow()

    body = {
        "Id": bundle_id,
        "CloudAccountId": d9_cloud_account,
        "cloudAccountType": 1,
        "IsTemplate": False

    }

    logging.debug(f"API call body - {body}")

    # body = {
    #    "CloudAccountId": "9facd1be-6593-4a1c-93eb-0122f745294d",
    #    "CloudAccountType": 1,
    #    "CloudNetwork": "",
    #    "Id": 137623,
    #    "IsTemplate": False,
    #    "Region": "",
    #    "description": "",
    #    "hideInCompliance": False,
    #    "minFeatureTier": "Trial",
    #    "name": "ATTest",
    #    "requestId": "d77ea68d-1c80-4556-8969-2511301fd17e"
    # }

    if region:
        d9region = region.replace('-', '_')  # dome9 identifies regions with underscores
        body["region"] = d9region

    logging.info("Dome9 Run Assessment Interface Version - {}".format(APIVersion))

    logging.info("Starting Assessment Execution")

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    r = requests.post('https://api.dome9.com/v2/assessment/bundleV2', data=json.dumps(body), headers=headers,
                      auth=(d9_key, d9_secret))
    r.raise_for_status()
    tn = datetime.datetime.utcnow()

    # check that max timeout was not reached
    if __checkThatMaxTimeWasNotReached(t0, maxTimeoutMinutes):
        return None

    total_sec = total_sec + (tn - t0).total_seconds()

    logging.info(f"Assessment Execution Done in {(tn - t0_run_assessment).total_seconds()} seconds \n")

    return r.json()


# Analyze the assessment execution result and return the assets id and types for all the assets the fail in
# each rule execution
def __print_map(failed_Test_relevant_entites_map):
    str = ""
    for test in failed_Test_relevant_entites_map:
        str += test.__str__() + "\n\t\tFailed Entities:\n"
        for entity in failed_Test_relevant_entites_map[test]:
            str += entity.__str__()
    return str


def __checkThatMaxTimeWasNotReached(t0, maxTimeoutMinutes):
    tNow = datetime.datetime.utcnow()
    elapsed = (tNow - t0).total_seconds()
    logging.info(f'Current run time of d9 assessment execution and analyzing is - {elapsed} Seconds')
    if elapsed > maxTimeoutMinutes * 60:
        logging.error(f'Stopping script, passed maxTimeoutMinutes ({maxTimeoutMinutes})')
        return True
    return False


def analyze_assessment_result(assessment_result,
                              region=None,
                              stack_name=None,
                              aws_profile=None,
                              maxTimeoutMinutes=10,
                              minimal_sevirity_to_fail=None):
    global t0, total_sec
    t0_run_assessment_analyze = datetime.datetime.utcnow()

    # resource_physical_ids - its a list of the resource ids that related to the stack_name and supported by Dome9
    # The ids are from the cfn describe and based on the PhysicalResourceId field list_of_failed_entities - It's a
    # list of FailedEntity that will contain for each failed entities in the assessment result it's id,arn,name,tags
    logging.info("Starting To Analyze Assessment Result")
    (resource_physical_ids, filed_tests_map) = __prepare_results_to_analyze(region=region,
                                                                            stack_name=stack_name,
                                                                            aws_profile=aws_profile,
                                                                            assessment_result=assessment_result)

    logging.info(f'Bundle - {assessment_result["request"]["name"]}')
    logging.info(f"Number of total failed tests: {len(filed_tests_map)}")
    # add statistics about the assessment result and print the stuck name
    failed_test_relevant_entities_map = dict()

    # get only the failed tests that contain entities from the deployed stack
    if stack_name is not None:
        logging.info(f"Failed Tests that are relevant to the Stack - {stack_name}:")
        for failed_test in filed_tests_map:
            fallback = True
            relevant_failed_entities = list()
            for failed_entity in filed_tests_map[failed_test]:
                # 1st check with the tags "key": "aws:cloudformation:stack-name" equals to our stack_name
                if failed_entity.tags:
                    for tag in failed_entity.tags:
                        if tag["key"] == "aws:cloudformation:stack-name" and tag["value"] == stack_name:
                            relevant_failed_entities.append(failed_entity)
                            fallback = False
                # 2nd if the entity doesn't have tags fall back to id
                if fallback and failed_entity.entity_id:
                    if failed_entity.entity_id in resource_physical_ids:
                        relevant_failed_entities.append(failed_entity)
                        fallback = False
                # 3rd fall back to name
                if fallback and failed_entity.name:
                    if failed_entity.name in resource_physical_ids:
                        relevant_failed_entities.append(failed_entity)
                        fallback = False
                # 4th fall back to arn
                if fallback and failed_entity.arn:
                    if failed_entity.arn in resource_physical_ids:
                        relevant_failed_entities.append(failed_entity)
                        fallback = False

            if len(relevant_failed_entities) > 0:
                failed_test_relevant_entities_map[failed_test] = relevant_failed_entities
    else:
        failed_test_relevant_entities_map = filed_tests_map

    if any(test.rule_severity == minimal_sevirity_to_fail for test in filed_tests_map):
        logging.info("Assessment was fail!!")
        logging.error(__print_map(failed_test_relevant_entities_map))
        exit(2)

    logging.info(__print_map(failed_test_relevant_entities_map))

    # check that max timeout was not reached
    if __checkThatMaxTimeWasNotReached(t0, maxTimeoutMinutes):
        return

    tn = datetime.datetime.utcnow()
    total_sec = total_sec + (tn - t0_run_assessment_analyze).total_seconds()
    logging.info(f"Assessment Analyzing Was Done in {(tn - t0_run_assessment_analyze).total_seconds()} seconds")

    return failed_test_relevant_entities_map


def __prepare_results_to_analyze(assessment_result, region=None, stack_name=None, aws_profile=None):
    """
    This method prepare the data model of the d9 assessment execution

    :param assessment_result: The result of the RunAssessment API
    :param region: the aws region where the Stack was deployed in case of assessment execution over specific Stack
    :param stack_name: the AWS stack name in case of assessment execution over specific Stack
    :param aws_profile: the AWS profiel that will use as cred to execute this script
    :return:
        tupple - resource_physical_ids, filed_tests_map

            resource_physical_ids - set of the physical Ids that belongs to resourses that was deployed part of the stack deployment
            filed_tests_map {
                FailedTest : [FailedEntity]
            }
    """
    aws_session = boto3.session.Session(profile_name=aws_profile,
                                        region_name=region) if aws_profile else boto3.session.Session(
        region_name=region)

    resource_physical_ids = None
    # In case of assessment execution for a specific AWS stack
    if stack_name is not None:
        # Get the AWS stack resources
        cfn = aws_session.client('cloudformation')
        response_pages = list()
        api_response = cfn.list_stack_resources(
            StackName=stack_name
        )

        logging.debug(api_response)

        response_pages.append(api_response)
        while 'NextToken' in api_response:
            api_response = cfn.list_stack_resources(
                StackName=stack_name,
                NextToken=api_response['NextToken']
            )
            response_pages.append(api_response)

        # get dome9 types from mapping file
        MAPPINGS_PATH = "%s/cfn_mappings.csv" % (os.path.dirname(os.path.realpath(__file__)))
        cfn_mappings = dict()
        with open(MAPPINGS_PATH, "r") as f:
            reader = csv.DictReader(f)
            for item in reader:
                if item['Dome9']:
                    cfn_mappings[item['CFN']] = item['Dome9'].split(',')

        # Prepare the set of physical resource ids for the relevant d9 supported resources from the stack
        resource_physical_ids = set()  # set will make it unique
        for response in response_pages:
            for resource in response['StackResourceSummaries']:
                resource_type = resource['ResourceType']
                resource_physical_id = resource["PhysicalResourceId"]
                if resource_type in cfn_mappings:
                    resource_physical_ids.add(resource_physical_id)

    # Prepare full entity representation (id,arn,name) of each failed entity
    filed_tests_map = dict()

    # for all the failed tests
    for test in [tst for tst in assessment_result["tests"] if not tst["testPassed"]]:
        failed_test = FailedTest()
        list_of_failed_entities = list()
        failed_test.set_rule_name(test["rule"]["name"])
        failed_test.set_rule_severity(test["rule"]["severity"])
        failed_test.set_rule_desc(test["rule"]["description"])

        filed_tests_map[failed_test] = None

        # for each failed asset
        for entity in [ast for ast in test["entityResults"] if ast["isRelevant"] and not ast["isValid"]]:
            entity_type = entity['testObj']['entityType']
            entity_idx = entity['testObj']["entityIndex"]
            if entity_idx >= 0:
                full_d9_entity = assessment_result["testEntities"][entity_type][entity_idx]
                failed_entity = FailedEntity()
                failed_entity.set_type(entity_type)
                # print(full_d9_entity_json)
                if 'id' in full_d9_entity:
                    failed_entity.set_entity_id(full_d9_entity["id"])
                if 'arn' in full_d9_entity:
                    failed_entity.set_arn(full_d9_entity["arn"])
                if 'name' in full_d9_entity:
                    failed_entity.set_name(full_d9_entity["name"])
                if 'tags' in full_d9_entity:
                    failed_entity.set_tags(full_d9_entity["tags"])
                list_of_failed_entities.append(failed_entity)
        filed_tests_map[failed_test] = list_of_failed_entities

    return resource_physical_ids, filed_tests_map


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

                                                ____ _  _ _  _    ____ ____ ____ ____ ____ ____ _  _ ____ _  _ ___
                                                |__/ |  | |\ |    |__| [__  [__  |___ [__  [__  |\/| |___ |\ |  | 
                                                |  \ |__| | \|    |  | ___] ___] |___ ___] ___] |  | |___ | \|  |          

'''

    text = (
        f'Script Version - {APIVersion} \n\n'
        'This is the Dome9 JIT assessment execution script \n'
        'It will trigger specific Dome9 bundle execution over specific cloud account\n'
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
    parser.add_argument('--bundleId', required=True, type=int,
                        help='the dome9 bundle id to execute')
    parser.add_argument('--maxTimeoutMinutes', required=False, type=int, default=10,
                        help='[the maximum time to wait to sync to finish]')
    parser.add_argument('--minimumSeverityForFail', required=False, type=int, default=-1,
                        help='[the minimal severity level that will cause fail - Dome9 rule severity (High/Medium/Low)] ')
    parser.add_argument('--log_file_path', required=False, type=str, default=None,
                        help='[the destination path of for the log]')
    parser.add_argument('--log_level', required=False, type=str, default='INFO',
                        help='[the execution level of the log]')
    args = parser.parse_args()
    __log_setup(log_file_path=args.log_file_path, log_level=args.log_level)
    # Take start time
    logging.info(f"Starting - Setting now (UTC {t0})")

    # If d9 representation id was not forward need
    # Need to get the Dome9 cloud account representation
    if args.cloudAccountD9Id is None:
        # allow to specify specific profile, fallback to standard boto credentials lookup strategy
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
        aws_session = boto3.session.Session(profile_name=args.awsCliProfile,
                                            region_name=args.region) if args.awsCliProfile else boto3.session.Session(
            region_name=args.region)
        sts = aws_session.client('sts')
        account_id = sts.get_caller_identity()["Account"]
        if (str(args.awsAccountNumber) != str(account_id)):
            logging.error(
                f'Error - the provided awsAccNumber ({args.awsAccountNumber}) is not tied to the AWS credentials of this script ({account_id}) consider providing a different "profile" argument')
            exit(2)
        logging.info(f'Resolving Dome9 account id from aws account number: {args.awsAccountNumber}')
        r = requests.get('https://api.dome9.com/v2/cloudaccounts/{}'.format(args.awsAccountNumber),
                         auth=(args.d9keyId, args.d9_secret))
        r.raise_for_status()
        d9_cloud_account = r.json()['id']
        logging.debug(f'Found it. Dome9 cloud account Id={d9_cloud_account}')
        cloudAccountD9Id = d9_cloud_account
    else:
        cloudAccountD9Id = args.cloudAccountD9Id

    result = run_assessment(bundle_id=args.bundleId,
                            d9_secret=args.d9secret,
                            d9_cloud_account=cloudAccountD9Id,
                            d9_key=args.d9keyId,
                            region=args.region,
                            maxTimeoutMinutes=args.maxTimeoutMinutes)

    if result is None:
        exit(1)

    res = analyze_assessment_result(assessment_result=result,
                                    region=args.region,
                                    stack_name=args.stackName,
                                    aws_profile=args.awsCliProfile,
                                    maxTimeoutMinutes=args.maxTimeoutMinutes)

    logging.info(f"Run and analyzing Assessment Script ran for {total_sec} seconds")
    return res


if __name__ == "__main__":
    main()
