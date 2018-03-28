#!/bin/bash

set -eux

PREFIX=ktsr42
ZIPFILE=process_temp_readings.zip
CODE_BUCKET=ktsr42.s3.code
CODE_BUCKET_PATH=code

PROFILE=root

Stackname="${PREFIX}_monitor_heating"

Sensorfile=/home/klaas/Projects/heating/testdata/sensor
ReaderUser=tsensor
AWSRegion=us-east-1

# make sure the $ZIPFILE is up to date
make

# Put the zipfile into S3
aws --profile $PROFILE s3 sync $ZIPFILE s3://$CODE_BUCKET/$CODE_BUCKET_PATH/$ZIPFILE

# Create/update the stack
aws --profile $PROFILE cloudformation wait deploy \
    --stack-name $Stackname \
    --template-file aws_setup.yaml \
    --parameter-overrides CommonPrefix=$PREFIX
    --capabilities CAPABILITY_IAM

# Create the access key if this was the stack creation
set +e
aws --profile $PROFILE iam create-access-key ${PREFIX}_heating_publisher > ../keys/${PREFIX}_heating_publisher_key.json
set -e

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
key_file=/home/$ReaderUserreleases/prod/access_key.json
bucket=$PREFIX.heating.s3
path=observations
prefix=obs
EOF

mv -vf new-read_temp_config.ini ../reader
