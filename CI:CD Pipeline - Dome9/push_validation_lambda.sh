#!/bin/bash

PROFILE=$1


rm -f codepipeline-lambda.zip

pushd codepipeline-lambda
zip -r ../codepipeline-lambda.zip * 
popd

if [ -z "$PROFILE" ]; then
    aws s3 cp 'codepipeline-lambda.zip'  s3://idan-dome9-cicd-pipeline/
else
    aws s3 cp --profile $PROFILE 'codepipeline-lambda.zip'  s3://idan-dome9-cicd-pipeline/
fi