PROFILE=default               # set the AWS cli profile that you want to use for creating the required AWS resources

PREFIX=                       # a prefix used for all aws resources that will be used for the deployment
CODE_BUCKET=                  # S3 bucket where the zipfile with the lambda code will be deposited. This must be an existing bucket
CODE_BUCKET_PATH=             # prefix (path) of the lambda code zipfile in the above bucket

Stackname="${PREFIX}MonitorHeating"   # This will be the AWS Cloudformation stack name, change it if you like

AWSRegion=us-east-1           # Select the AWS region to use
BucketName=$PREFIX.heating.s3 # We will create a new S3 bucket to store all temperature measurements. Change the name if necessary

# Config settings for the sensor reader on the RPI
ReaderUser=tsensor            # user id under which the reader script will run on the Raspberry PI
Sensorfile=/home/$ReaderUser/sensorfile  # Path to the file for reading the current sensor measurement. It might be best to make this a symbolic link

# Config items for the receiver on AWS lambda
Phonenumber=                  # Where to send the SMS alerts
MinimumTemp=3                 # Send an alert if the temperature reading drops below this (degrees Celsius)
RepeatAlertHours=3            # Repeat the alert after this many hours if nothing changes
MaxDelay=15                   # Send an alert if the temperature reading is this many minutes delayed

