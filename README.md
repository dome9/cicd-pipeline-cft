# CFT based CI/CD pipeline with Dome9
These scripts demonstrate how use the SyncNow and EntityFetchStatus APIs to integrate Dome9 Compliance Engine assessments after a new test CFT stack was deployed as part of a CI/CD pipline. 

The script `d9_sync_and_wait.py`:
- Analyzes the exact CFT types that are used in the relevant stack
- Determines which relevant Dome9 types are related to the CFT types
- Calls Dome9 `SyncNow` API for the relevant cloud account
- Polls Dome9 `EntityFetchStatus` API to determine when all relevant types have been updated (fetched) by the system
- Exit cleanly (code 0) when all entity types are fetched or with an error if timeout occured after `maxTimeoutMinutes`

This code should be integrated into a CI/CD pielines followed by a step to perfrom an ad-hoc Dome9 Compliance Engine Assessment.


## install dependecies (if they are not already installed)

```
pip install boto3
pip install requests
```

## running the sample
- get your Dome9 API keys and make sure you have an AWS credentials profile for the relevant AWS account
- copy sample.sh or modify it with your own settings.
```
$ ./sample.sh
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