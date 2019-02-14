#!/bin/bash

PROFILE=$1


rm -f codepipeline-lambda.zip

pushd codepipeline-lambda
zip -r ../codepipeline-lambda.zip * 
popd

if [ -z "$PROFILE" ]; then
    aws s3 cp 'codepipeline-lambda.zip'  s3://<bucket_name>/
else
    aws s3 cp --profile $PROFILE 'codepipeline-lambda.zip'  s3://<bucket_name>/
fi