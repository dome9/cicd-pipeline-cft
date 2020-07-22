python d9_sync_and_wait.py  \
    --d9keyId <your dome9 api key Id> \
    --d9secret <your dome9 api secret> \
    --awsCliProfile default \
    --awsAccountNumber 123456789 \
    --region us-east-1 \
    --stackName my-stack \
    --excludedTypes 'LogGroups,IamCredentialReport'
