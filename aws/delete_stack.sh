#!/bin/bash

set -eux

source settings.sh

aws --profile $PROFILE s3 rb s3://$BucketName --force
aws --profile $PROFILE cloudformation delete-stack --stack-name $Stackname
aws --profile $PROFILE cloudformation wait stack-delete-complete --stack-name $Stackname
