"""Summary

Attributes:
    AWS_CIS_BENCHMARK_VERSION (str): Description
    CONFIG_RULE (bool): Description
    CONTROL_1_1_DAYS (int): Description
    REGIONS (list): Description
    SCRIPT_OUTPUT_JSON (bool): Description
"""

from __future__ import print_function
import json
import csv
import time
import sys
import re
import tempfile
from datetime import datetime
import boto3
import botocore
import traceback
import zipfile

import os
from base64 import b64decode
from utils import get_user_params
from dome9.d9_run_assessment import run_assessment
from dome9.d9_run_assessment import analyze_assessment_result
from dome9.d9_sync_and_wait import d9_sync_and_wait



print('loading encrypted Dome9 Credentials')
# Decrypt code should run once and variables stored outside of the function
# handler so that these are decrypted once per container
KEY_ENCRYPTED = os.environ['d9key']
KEY_DECRYPTED = boto3.client('kms').decrypt(CiphertextBlob=b64decode(KEY_ENCRYPTED))['Plaintext']
print("KEY_DECRYPTED=%s" % KEY_DECRYPTED)

SECRET_ENCRYPTED = os.environ['d9secret']
SECRET_DECRYPTED = boto3.client('kms').decrypt(CiphertextBlob=b64decode(SECRET_ENCRYPTED))['Plaintext']


# Would you like to print the results as JSON to output?
SCRIPT_OUTPUT_JSON = True
code_pipeline = boto3.client('codepipeline')
EC2_CLIENT = boto3.client('ec2')
cf = boto3.client('cloudformation')


def put_job_success(job, message):
    """Notify CodePipeline of a successful job

    Args:
        job: The CodePipeline job ID
        message: A message to be logged relating to the job status

    Raises:
        Exception: Any exception thrown by .put_job_success_result()

    """
    print('Putting job success')
    print(message)
    code_pipeline.put_job_success_result(jobId=job)


def put_job_failure(job, message):
    """Notify CodePipeline of a failed job

    Args:
        job: The CodePipeline job ID
        message: A message to be logged relating to the job status

    Raises:
        Exception: Any exception thrown by .put_job_failure_result()

    """
    print('Putting job failure')
    print(message)
    code_pipeline.put_job_failure_result(jobId=job, failureDetails={'message': message, 'type': 'JobFailed'})


def continue_job_later(job, message):
    """Notify CodePipeline of a continuing job

    This will cause CodePipeline to invoke the function again with the
    supplied continuation token.

    Args:
        job: The JobID
        message: A message to be logged relating to the job status
        continuation_token: The continuation token

    Raises:
        Exception: Any exception thrown by .put_job_success_result()

    """

    # Use the continuation token to keep track of any job execution state
    # This data will be available when a new job is scheduled to continue the current execution
    continuation_token = json.dumps({'previous_job_id': job})

    print('Putting job continuation')
    print(message)
    code_pipeline.put_job_success_result(jobId=job, continuationToken=continuation_token)


def stack_exists(stack):
    """Check if a stack exists or not

    Args:
        stack: The stack to check

    Returns:
        True or False depending on whether the stack exists

    Raises:
        Any exceptions raised .describe_stacks() besides that
        the stack doesn't exist.

    """
    try:
        cf.describe_stacks(StackName=stack)
        return True
    except botocore.exceptions.ClientError as e:
        if "does not exist" in e.response['Error']['Message']:
            return False
        else:
            raise e


def delete_stack(stack):
    """CloudFormation stack deletion

    Args:
        stack: The stack to be created

    Throws:
        Exception: Any exception thrown by .create_stack()
    """
    cf.delete_stack(StackName=stack)


# --- Security Groups ---
# 4.1 Ensure no security groups allow ingress from 0.0.0.0/0 to port 22 (Scored)
# Deprecatged  - No need any more using the run assessment API
#def control_4_1_ensure_ssh_not_open_to_world(regions, stackName):
#    """Summary
#
#    Returns:
#        TYPE: Description
#    """
#    result = True
#    failReason = ""
#    offenders = []
#    control = "4.1"
#    description = "Ensure that security groups allow ingress from approved CIDR range to port 22"
#    scored = True
#    for n in regions:
#        client = boto3.client('ec2', region_name=n)
#        response = client.describe_security_groups(
#            Filters=[{'Name': 'tag:aws:cloudformation:stack-name', 'Values': [stackName]}])
#        for m in response['SecurityGroups']:
#            if "72.21.196.67/32" not in str(m['IpPermissions']):
#                for o in m['IpPermissions']:
#                    try:
#                        if int(o['FromPort']) <= 22 <= int(o['ToPort']):
#                            result = False
#                            failReason = "Found Security Group with port 22 open to the wrong source IP range"
#                            offenders.append(str(m['GroupId']))
#                    except:
#                        if str(o['IpProtocol']) == "-1":
#                            result = False
#                            failReason = "Found Security Group with port 22 open to the wrong source IP range"
#                            offenders.append(str(n) + " : " + str(m['GroupId']))
#    return {'Result': result, 'failReason': failReason, 'Offenders': offenders, 'ScoredControl': scored,
#            'Description': description, 'ControlId': control}


def get_regions():
    region_response = EC2_CLIENT.describe_regions()
    regions = [region['RegionName'] for region in region_response['Regions']]
    return regions

def json_output(controlResult):
    """Summary

    Args:
        controlResult (TYPE): Description

    Returns:
        TYPE: Description
    """
    inner = dict()
    outer = dict()
    for m in range(len(controlResult)):
        inner = dict()
        for n in range(len(controlResult[m])):
            x = int(controlResult[m][n]['ControlId'].split('.')[1])
            inner[x] = controlResult[m][n]
        y = controlResult[m][0]['ControlId'].split('.')[0]
        outer[y] = inner
    print("JSON output:")
    print("-------------------------------------------------------")
    print(json.dumps(outer, sort_keys=True, indent=4, separators=(',', ': ')))
    print("-------------------------------------------------------")
    print("\n")
    print("Summary:")
    print(shortAnnotation(controlResult))
    print("\n")
    return 0


def shortAnnotation(controlResult):
    """Summary

    Args:
        controlResult (TYPE): Description

    Returns:
        TYPE: Description
    """
    annotation = []
    longAnnotation = False
    for m, _ in enumerate(controlResult):
        for n in range(len(controlResult[m])):
            if controlResult[m][n]['Result'] is False:
                if len(str(annotation)) < 220:
                    annotation.append(controlResult[m][n]['ControlId'])
                else:
                    longAnnotation = True
    if longAnnotation:
        annotation.append("etc")
        return "{\"Failed\":" + json.dumps(annotation) + "}"
    else:
        return "{\"Failed\":" + json.dumps(annotation) + "}"


def lambda_handler(event, context):
    """Summary
            This Lambda going to execute two Dome9 API Calls
            1. sync now - Enforce Dome9 to execute fetch and load all the entities data to Dome9 (so it will now include your test stack entites)
            2. run assessment - execute a given Dome9 assessment bundle and analyze thew results related to the test stack

    Args:
        event (TYPE): Description
        context (TYPE): Description

    Returns:
        TYPE: Description
    """

    # Print the entire event for tracking
    print("Received event: " + json.dumps(event, indent=2))

    # Extract the Job ID
    job_id = event['CodePipeline.job']['id']

    # Globally used resources
    region_list = get_regions()

    # Extract the Job Data
    job_data = event['CodePipeline.job']['data']

    params = get_user_params(job_data)

    stackName = params['stackName']
    region = params['region']
    aws_account = params['awsAccount']
    bundleId = params['bundelId']
    excludedTypes = ['LogGroups,IamCredentialReport']


    print("stackName: " + stackName)
    print("Going to execute Sync and wait API call")

    t0_syn_and_wait = datetime.utcnow()

    st = d9_sync_and_wait(awsAccNumber=aws_account, region=region, stackName=stackName,
                          excludedTypes=excludedTypes, maxTimeoutMinutes=10,
                          d9keyId=KEY_DECRYPTED, d9secret=SECRET_DECRYPTED)

    t2_syn_and_wait = datetime.datetime.utcnow()
    print("\n" + "*" * 50 + "\nRun \"Sync And Wait\" Script ran for {} seconds\n".format(
        (t0_syn_and_wait - t2_syn_and_wait).total_seconds()) + "*" * 50 + "\n")

    if (st.isAllCompleted()):
        print("\n*** All supported services were successfully updated (fetched) ***\n")
        print("Going to run assessment analysing related to the test stack - {}".format(stackName))

        t0_run_assessment = datetime.utcnow()

        result = run_assessment(bundle_id=bundleId, aws_cloud_account=aws_account,
                                d9_secret=SECRET_DECRYPTED,d9_key=KEY_DECRYPTED, region=region)

        res = analyze_assessment_result(assessment_result=result, aws_cloud_account=aws_account,
                                        region=region, stack_name=stackName)

        tn_run_assessment = datetime.utcnow()

        print("\n" + "*" * 50 + "\nRun and analyzing Assessment Script ran for {} seconds\n".format(
            (t0_run_assessment - tn_run_assessment).total_seconds()) + "*" * 50 + "\n")

        if len(res) == 0:
            put_job_success(job_id,"Stack simulation and validation was succeeded. No Compliance violation for Dome9  BundelId - {} were found  ".format(bundleId))
        else:
            if stack_exists(stackName):
                delete_stack(stackName)
            put_job_failure(job_id,"Run Assessment was failed for stack - {}. result - {}".format(stackName, res))
    else:
        put_job_failure(job_id, "not all types were updated. Those are the types that their dome9 fetch is still pending -  {}".format(",".join(st.pending)))

