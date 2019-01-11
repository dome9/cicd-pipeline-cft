#!/bin/bash

# a 'deployment' script based on S3
# In real world we would probably have a pipline configured to our git repository
rm -f my-app-cft.zip
zip -r my-app-cft.zip my-app-cft
aws s3 cp 'my-app-cft.zip'  s3://reinvent2017sid317/
