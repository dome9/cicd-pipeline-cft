
# CFT based CI/CD pipeline with Dome9
The Dome9 CI/CD pipeline contain two steps - </br>

 1.Sync and wait execution - Which trigger Dome9 fetch and sync execution </br>
 
 2.Run Assessment - Which Execute a specific assessment in a specific AWS region and anlyze result for a specific stack name
 
 
## install dependecies (if they are not already installed)

```
pip install boto3
pip install requests
```

#### Support python versions
- 2.7.1
- 3.6.5
- 3.7.1

## Sync And Wait Step 
These script demonstrate how use the SyncNow and EntityFetchStatus APIs to integrate Dome9 Compliance Engine assessments after a new test CFT stack was deployed as part of a CI/CD pipeline. 

The script `d9_sync_and_wait.py`:
- Analyzes the exact CFT types that are used in the relevant stack
- Determines which relevant Dome9 types are related to the CFT types
- Calls Dome9 `SyncNow` API for the relevant cloud account
- Polls Dome9 `EntityFetchStatus` API to determine when all relevant types have been updated (fetched) by the system
- Exit cleanly (code 0) when all entity types are fetched or with an error if timeout occurred after `maxTimeoutMinutes`

This code should be integrated into a CI/CD pipelines followed by a step to perform an ad-hoc Dome9 Compliance Engine Assessment.


### running the sample
- get your Dome9 API keys and make sure you have an AWS credentials profile for the relevant AWS account
- copy `sample_run_sync_wait.sh` or modify it with your own settings.
```
$ ./sample_run_sync_wait.sh
Starting...
Setting now (UTC 2018-09-22 03:10:55.172242) as base time

CFN types found in this stack (10):
-----------------------------------
AWS::Lambda::Permission
AWS::IAM::Role
AWS::ApiGateway::RestApi
AWS::Lambda::Function
AWS::Logs::LogGroup
AWS::ApiGateway::Resource
AWS::S3::Bucket
AWS::Lambda::Version
AWS::ApiGateway::Deployment
AWS::ApiGateway::Method

relevant CFN types SUPPORTED by Dome9 (6):
------------------------------------------
AWS::Lambda::Permission
AWS::IAM::Role
AWS::Lambda::Function
AWS::Logs::LogGroup
AWS::S3::Bucket
AWS::Lambda::Version

relevant CFN types NOT supported by Dome9 (4):
----------------------------------------------
AWS::ApiGateway::RestApi
AWS::ApiGateway::Resource
AWS::ApiGateway::Deployment
AWS::ApiGateway::Method

Excluded types (will not wait for them) (2):
--------------------------------------------
LogGroups
IamCredentialReport

Actual Dome9 types to wait for (5):
-----------------------------------
IamRole
S3Bucket
IamRoleInlinePolicies
Lambda
IamRoleAttachedPolices
resolving Dome9 account id from aws account number: 1234567890
Found it. Dome9 cloud account Id=2eb1a21c-36c8-4222-b99a-32cce7b0c7ee

Sending Dome9 SyncNow command...
{u'externalAccountNumber': u'1234567890', u'cloudAccountId': u'2eb1a21c-36c8-4222-b99a-32cce7b0c7ee', u'workFlowId': u'd8b58af3-bb1f-4aea-b0f6-610704bba7d5', u'name': u'froyke RO'}
Querying entities fetch status from Dome9 API...

Completed (4):
--------------
S3Bucket
IamRoleInlinePolicies
Lambda
IamRoleAttachedPolices

Pending (1):
------------
IamRole

Not done yet. Will sleep a bit and poll the status again...
Querying entities fetch status from Dome9 API...

Completed (5):
--------------
IamRole
S3Bucket
IamRoleInlinePolicies
Lambda
IamRoleAttachedPolices

Pending (0):
------------


*** All supported services were successfully updated (fetched) ***
```

## Run Assessment Step
These script demonstrate how use the Assessment API for specific aws account and region and analyze the result based on a given stack name  

The script `d9_run_assessment.py`:
- Execute a specific Dome9's assessment based on the given parameter  `bundleId`
- Analyze the run assessment result and return a data structure that represent the failed tests and entities that related to the given parameter `stackName` 
- Determines which relevant Dome9 types are related to the CFT types
- Exit cleanly (code 0)

This code should be integrated into a CI/CD pipelines.


### Running the sample
- get your Dome9 API keys and make sure you have an AWS credentials profile for the relevant AWS account
- copy `sample_run_assessment.sh`  or modify it with your own settings.
```
$ ./sample_run_assessment.sh
********************************************************************************
Starting...
********************************************************************************

Setting now (UTC 2018-12-17 19:24:28.635800) 

**************************************************
Starting Assessment Execution
**************************************************

Resolving Dome9 account id from aws account number: 1234567890
Found it. Dome9 cloud account Id=b7197e73-04c2-4eb3-9f80-da2e842ed5ac

**************************************************
Assessment Execution Done in 6.935792 seconds 
**************************************************

**************************************************
Starting To Analyze Assessment Result
**************************************************


Bundle - AWS Dome9 Network Alerts

Number of total failed tests: 13


Failed Tests that are relevant to the Stack - MyStackExample:

	Test:
		rule name: Security Groups - with admin ports too exposed to the public internet
		severity: High


		Failed Entities:

			Entity:
			type: securityGroup
			name: MyStackExample-InstanceSecurityGroup-RNHDX4FYJR54
			id: sg-00d5387eeb014b60c

	Test:
		rule name: Restrict outbound traffic to that which is necessary, and specifically deny all other traffic
		severity: Medium


		Failed Entities:

			Entity:
			type: securityGroup
			name: MyStackExample-InstanceSecurityGroup-RNHDX4FYJR54
			id: sg-00d5387eeb014b60c

	Test:
		rule name: Ensure no security groups allow ingress from 0.0.0.0/0 to SSH (TCP:22)
		severity: High


		Failed Entities:

			Entity:
			type: securityGroup
			name: JR54-InstanceSecurityGroup-RNHDX4FYRJ45
			id: sg-00d5387eeb014b60c

	Test:
		rule name: Instance with administrative service: SSH (TCP:22) is too exposed to the public internet
		severity: High


		Failed Entities:

			Entity:
			type: instance
			name: 
			id: i-06c523fb832a0531f

	Test:
		rule name: Process for Security Group Management - Managing security groups
		severity: High


		Failed Entities:

			Entity:
			type: securityGroup
			name: MyStackExample-InstanceSecurityGroup-RNHDX4FYJR54
			id: sg-00d5387eeb014b60c

	Test:
		rule name: Instance with administrative service: SSH (TCP:22) is exposed to a wide network scope
		severity: Medium


		Failed Entities:

			Entity:
			type: instance
			name: 
			id: i-06c523fb832a0531f


**************************************************
Assessment Analyzing Was Done in 8.337687 seconds
**************************************************

Script ran for 8.336446 seconds
```

### Embed in CI/CD pipeline 
The script `d9_run_assessment.py` has a well defined API so it can be embed in other processes


Add the next line to your python script
```
from d9_run_assessment import run_assessment
from d9_run_assessment import analyze_assessment_result
```

Then you can preform the next calls:
```
assessment_execution_result = run_assessment(<bundel_id>, <aws_account number>, <dome9 secret>,<dome9 key>,<aws_region>)

assessment_analyze_result  = analyze_assessment_result(res,<aws_account number>,<aws_region>,<cft stack name>)
```
Where `assessment_analyze_result` is a data structure that represents the failed tests and relevant entities to the given stack name 
`assessment_analyze_result` it's a map: `{FailedTest ----> [FailedEntity]}`

FailedTest -  represents a Dome9 test that was part of the executed assessment it contains these properties: 
- rule_name
- rule_desc
- rule_severity

FailedEntity -  represents an AWS entity that was part of the CFT stack name and failed in a dome9 test. It contains these properties:
- entity_id
- name
- tags - {key:value}
- type


