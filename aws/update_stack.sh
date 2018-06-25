#!/bin/bash

set -eux

source settings.sh

ZIPFILE=process_temp_readings.zip

# make sure the $ZIPFILE is up to date
make $ZIPFILE

# Put the zipfile into S3
aws --profile $PROFILE s3 cp $ZIPFILE s3://$CODE_BUCKET/$CODE_BUCKET_PATH/$ZIPFILE

if aws --profile $PROFILE cloudformation list-stacks \
	| jq '.StackSummaries|.[] | select(.StackStatus != "DELETE_COMPLETE") | .StackName' \
	| grep -q $Stackname
then
    ## Update stack
    aws --profile $PROFILE cloudformation update-stack \
	--stack-name $Stackname \
	--template-body file://aws_setup.yaml \
	--parameters ParameterKey=CommonPrefix,ParameterValue=$PREFIX ParameterKey=BucketName,ParameterValue=$BucketName \
	--capabilities CAPABILITY_NAMED_IAM

    aws --profile $PROFILE cloudformation wait stack-update-complete --stack-name $Stackname
else
    ## create stack
    aws --profile $PROFILE cloudformation create-stack \
	--stack-name $Stackname \
	--template-body file://aws_setup.yaml \
	--parameters ParameterKey=CommonPrefix,ParameterValue=$PREFIX ParameterKey=BucketName,ParameterValue=$BucketName \
	--capabilities CAPABILITY_NAMED_IAM

    aws --profile $PROFILE cloudformation wait stack-create-complete --stack-name $Stackname
    
    aws --profile $PROFILE iam create-access-key --user-name ${PREFIX}_heating_publisher > ../keys/publisher_key.json
    
    cat > new-read_temp_config.ini  <<EOF
[Input]	
Sensorfile=$Sensorfile
HistoryDir=/home/$ReaderUser/data
Logfiles=/home/$ReaderUser/logs/reader_log
FilePrefix=reading
MaxReadings=20
LogLevel=info

[AWS]
region=$AWSRegion
key_file=/home/$ReaderUser/releases/prod/publisher_key.json
bucket=$BucketName
path=observations
prefix=obs
EOF

    mv -vf new-read_temp_config.ini ../reader/read_temp_config.ini
fi

cat >> new-receiver_config.json <<EOF
{
    "minimum_temperature":$MinimumTemp,
    "repeat_alert_hours":$RepeatAlertHours,
    "phonenumber":$Phonenumber,
    "max_delay":$MaxDelay
}
EOF

mv new-receiver_config.json receiver_config.json
aws --profile $PROFILE s3 cp receiver_config.json s3://$BucketName/lambda_internal/receiver_config.json

