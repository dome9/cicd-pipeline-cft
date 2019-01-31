#!/bin/bash

# a 'deployment' script based on S3
# In real world we would probably have a pipline configured to our git repository

PROFILE=$1

rm -f my-app-cft.zip
pushd my-app-cft
zip -r ../my-app-cft.zip *
popd

if [ -z "$PROFILE" ]; then
    aws s3 cp 'my-app-cft.zip'  s3://idan-dome9-cicd-pipeline/
else
    aws s3 cp --profile $PROFILE 'my-app-cft.zip'  s3://idan-dome9-cicd-pipeline/
fi
