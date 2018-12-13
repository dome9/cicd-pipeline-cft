# 3rd party libraries
import boto3  # $ pip install boto3
import requests  # $ pip install requests

# python standard libraries
import json
import csv
import argparse
import datetime


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
        rep += ''.join(filter(None, ["\t\t\ttype: ", self.type, "\n"]))
        rep += ''.join(filter(None, ["\t\t\tname: ", self.name, "\n"]))
        rep += ''.join(filter(None, ["\t\t\tid: ", self.entity_id, "\n"]))
        rep += ''.join(filter(None, ["\t\t\tarn: ", self.arn, "\n"]))

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
        rep = "\tRule:\n"
        rep += "\t\tname: " + self.rule_name + "\n"
        rep += "\t\tseverity: " + self.rule_severity + "\n"
        # rep += "\t\tdescription: " + self.rule_desc + "\n"

        return rep


def run_assessment(bundle_id, aws_cloud_account, d9_secret, d9_key, d9region, d9_cloud_account=""):
    print("\n"+"*" * 36 + "\nStart Assessment Execution\n" + "*" * 36)
    d9_id = ""
    # Need to get the Dome9 cloud account representation
    if d9_cloud_account == "":
        print('\nResolving Dome9 account id from aws account number: {}'.format(aws_cloud_account))
        r = requests.get('https://api.dome9.com/v2/cloudaccounts/{}'.format(aws_cloud_account),
                         auth=(d9_key, d9_secret))
        d9_id = r.json()['id']
        print('Found it. Dome9 cloud account Id={}'.format(d9_id))

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    body = {
        "id": bundle_id,
        "cloudAccountId": d9_id,
        "region": d9region,
        "cloudAccountType": "Aws"
    }

    r = requests.post('https://api.dome9.com/v2/assessment/bundleV2', data=json.dumps(body), headers=headers,
                      auth=(d9_key, d9_secret))

    print("\n"+"*" * 36 + "\nAssessment Execution Done\n" + "*" * 36)

    return r.json()


# Analyze the assessment execution result and return the assets id and types for all the assets the fail in
# each rule execution

def print_map(failed_Test_relevant_entites_map):
    for test in failed_Test_relevant_entites_map:
        print(test)
        print("\n\t\tFailed Entities:\n")
        for entity in failed_Test_relevant_entites_map[test]:
            print(entity)



def analyze_assessment_result(assessment_result, aws_cloud_account, region, stack_name, aws_profile=''):
    # resource_physical_ids - its a list of the resource ids that related to the stack_name and supported by Dome9
    # The ids are from the cfn describe and based on the PhysicalResourceId field list_of_failed_entities - It's a
    # list of FailedEntity that will contain for each failed entities in the assessment result it's id,arn,name,tags
    print("\n"+"*" * 36 + "\nStart To Analyze Assessment Result\n" + "*" * 36+"\n")
    print("\nBundle - {}".format(assessment_result["request"]["name"]))
    print("\nFailed Tests:\n")

    (resource_physical_ids, filed_tests_map) = prepare_results_to_analyze(aws_cloud_account, region, stack_name,
                                                                          aws_profile, assessment_result)
    failed_Test_relevant_entites_map = dict()
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
            failed_Test_relevant_entites_map[failed_test] = relevant_failed_entities

    print_map(failed_Test_relevant_entites_map)

    print("\n"+"*" * 36 + "\nAssessment Analyzing Was Done\n" + "*" * 36+"\n")


def prepare_results_to_analyze(aws_cloud_account, region, stack_name, aws_profile, assessment_result):
    # allow to specify specific profile, fallback to standard boto credentials lookup strategy
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
    aws_session = boto3.session.Session(profile_name=aws_profile,
                                        region_name=region) if aws_profile else boto3.session.Session(
        region_name=region)

    # sanity test - verify that we have credentials for the relevant AWS account numnber
    sts = aws_session.client('sts')
    account_id = sts.get_caller_identity()["Account"]
    if (aws_cloud_account != account_id):
        print(
            'Error - the provided awsAccNumber ({}) is not tied to the AWS credentials of this script ({}) consider '
            'providing a different "profile" argument'.format(
                aws_cloud_account, account_id))
        exit(2)

    cfn = aws_session.client('cloudformation')
    response = cfn.list_stack_resources(
        StackName=stack_name,
        # NextToken='string' # TODO handle pagination
    )

    # get dome9 types from mapping file
    MAPPINGS_PATH = "./cfn_mappings.csv"
    cfn_mappings = dict()
    with open(MAPPINGS_PATH, "r") as f:
        reader = csv.DictReader(f)
        for item in reader:
            if item['Dome9']:
                cfn_mappings[item['CFN']] = item['Dome9'].split(',')

    # Prepare the set of physical resource ids for the relevant d9 supported resources from the stack
    resource_physical_ids = set()  # set will make it unique
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--d9keyId', required=True, type=str)
    parser.add_argument('--d9secret', required=True, type=str)
    parser.add_argument('--awsCliProfile', required=False, type=str)
    parser.add_argument('--awsAccountNumber', required=True, type=str)
    parser.add_argument('--d9CloudAccount', required=False, type=str, default='')
    parser.add_argument('--region', required=True, type=str)
    parser.add_argument('--stackName', required=True, type=str)
    parser.add_argument('--bundleId', required=True, type=int)
    parser.add_argument('--maxTimeoutMinutes', required=False, type=int, default=10)
    args = parser.parse_args()

    # Take start time
    t0 = datetime.datetime.utcnow()
    print("\n\n{}\nStarting...\n{}\n\nSetting now (UTC {}) ".format(80 * '*', 80 * '*', t0))
    d9region = args.region.replace('-', '_')  # dome9 identifies regions with underscores
    result = run_assessment(bundle_id=args.bundleId, aws_cloud_account=args.awsAccountNumber, d9_secret=args.d9secret,
                            d9_key=args.d9keyId,d9region=d9region)

    analyze_assessment_result(assessment_result=result, aws_cloud_account=args.awsAccountNumber, region=args.region,
                              stack_name=args.stackName, aws_profile=args.awsCliProfile)

    t2 = datetime.datetime.utcnow()
    print('Script ran for {} seconds'.format((t2 - t0).total_seconds()))
    exit(0)
