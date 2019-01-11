#!/bin/bash
pushd codepipeline-lambda
zip -r ../codepipeline-lambda.zip * 
popd
aws s3 cp 'codepipeline-lambda.zip'  s3://reinvent2017sid317/