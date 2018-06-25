PREFIX=ktsr42
ZIPFILE=process_temp_readings.zip
CODE_BUCKET=ktsr42.s3.code
CODE_BUCKET_PATH=code

PROFILE=root

Stackname="${PREFIX}MonitorHeating"

ReaderUser=tsensor
Sensorfile=/home/$ReaderUser/sensorfile
AWSRegion=us-east-1
BucketName=$PREFIX.heating.s3
