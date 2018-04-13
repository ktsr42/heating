#!/bin/bash

set -eux

PREFIX=ktsr42
PROFILE=root

BucketName=$PREFIX.heating.s3
Stackname="${PREFIX}MonitorHeating"


aws --profile $PROFILE s3 rb s3://$BucketName --force
aws --profile $PROFILE cloudformation delete-stack --stack-name $Stackname
aws --profile $PROFILE cloudformation wait stack-delete-complete --stack-name $Stackname
