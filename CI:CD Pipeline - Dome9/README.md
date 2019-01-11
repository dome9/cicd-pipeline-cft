# DevSecOps in the CI/CD pipeline

## Setup Dome9 account (www.dome9.com)
1. Make sure you have access to a Dome9 account (www.dome9.com)
1. Generate Dome9 (v2) API keys at : https://secure.dome9.com/v2/settings/credentials (and write the key Id and secret)
1. Select a predefined or create a compliance engine bundle and write its ID (visible at the URL)

## Setup
1. Create 2 VPCs in your desired account (1 for prod , 1 for test)
1. Create your own S3 bucket in the desired region and enable versioning on the bucket 
1. Review the folder my-app-cft , UPDATE the "test-stack-configuration.json" and "prod-stack-configuration.json" files with your VPC IDs.
1. Review the 2 push___.sh scripts and *modify* your S3 bucket name
1. Upload the pipline code to S3 by invoking `./push_validation_lambda.sh`
1. Create new stack in the CloudFormation service using `pipeline-cft.json`
1. Fill parameters or take the default values. Note to fill your Dome9 bundle ID 

it'll take about 2 minutes for the pipeline to be created.

## Setting up encrypted parameters (Dome9 credentials)
1. Once the CFN service finish creating your pipeline, go to the Lambda console and add 2 (encrypted) parameters to the `CFNValidateLambda...`:
    1. d9key - your Dome9 v2 api key (that you copied before)
    1. d9secret - your Dome9 v2 secret (that you copied before)

Use the newly created `DevSecOpsPiplineKey` KMS key to encrypt the values

## Money time...
1. deploy your app code to S3 by running `./push_app.sh`. The code pipline should catch it automatically and start the pipline.
