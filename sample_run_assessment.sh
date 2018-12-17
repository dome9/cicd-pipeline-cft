#!/usr/bin/env bash
python d9_run_assessment.py  \
    --d9keyId <your dome9 api key Id> \
    --d9secret <your dome9 api secret> \
    --awsCliProfile default \
    --awsAccountNumber 123456789 \
    --d9CloudAccount <yor d9 cloud account if you have it - optional> \
    --region <AWS region i.e us-east-1> \
    --stackName <your cloud formation stack name> \
    --bundleId <the d9 id that represent this assessment - i.e -4 for d9 based practice sample>
