# Temperature Monitor

## Abstract

This project provides continuous monitoring of a DS18B20 temperature
sensor using AWS (Amazon Web Services). All code is written in
Python. The temperature sensor is attached to a Raspberry PI. It sends
alerts via SMS if a reading is below a given threshold.

## How it works

Whenever it is run, the temperature reader script on the RPI will take
the current reading of the sensor, store it locally and then also
store it in a file in the S3 bucket created for this purpose. The
upload to the S3 bucket triggers the execution of
aws/process_temp_readings.py as an AWS lambda function. This function
does all the heavy lifting, i.e. it consolidates the raw readings into
json files by date and writes them to a separate directory in the AWS
bucket.  It also checks if the latest reading is not too old or if it
is below the set threshold and sends alert messages to the configured
SMS number.

The same AWS lambda function is also invoked from AWS on a schedule so
that it can detect that the RPI has stopped sending updates and alert
accordingly.

At this point the code only supports monitoring one temperature
sensor.

## Background

I created this project as a way to monitor the temperature of a
heating pipe in our house that can freeze up during the winter if we
are not careful. It uses a Raspberry PI to take readings at regular
intervals. The result is pushed into an AWS S3 bucket, which triggers
an AWS lambda function that processes the data and sends out any
alerts that are considered relevant. Most importantly the Lambda
function will send alerts if the measured temperature drops below a
configured threshold. However, it will also send alerts if no updates
have been received for some time (default is 4 hours).

## Requirements
 
You will need at least a Raspberry PI and an AWS account plus a
temperature sensor. My setup includes a regular PC with Linux (Ubuntu)
installed and I will describe the installation process assuming such
an environment. If you do not have a Linux computer, you can probably
do everything on the PI though I have not tested that.

Unfortunately there are no ready-made temperature sensors for the
Raspberry PI that can simply be plugged into the GPIO
connector. Instead you will have to make your own by buying the sensor
and wiring it up yourself. It is not too hard, I could figure it out,
even though I barely know which end of a soldering iron gets
hot. Instructions on how to connect a DS18B20 sensor to the PI are
here
https://www.cl.cam.ac.uk/projects/raspberrypi/tutorials/temperature/
(a bit old by now) or here
https://pimylifeup.com/raspberry-pi-temperature-sensor/.

# Installation Procedure

## Preparations 

### AWS Account

If you do not have an AWS account, you will have to create one. Open
http://aws.amazon.com and click on the "Sign Up" button in the top
right corner. Note that you will have to supply a credit card to
create the AWS account. When used with one Raspberry PI, the AWS
resource usage should stay within the free tier of AWS.

### Raspberry PI

On the Raspberry PI, you need to install the following items:

* Python 3: `sudo apt-get install python3`
* pipenv:   `sudo pip3 install pipenv`

You should also create a dedicated user that will run the temperature
reading code. I called it 'tsensor': `sudo adduser tsensor`.

### Linux Work Machine Configuration

You need to install the following items:

* Python 3: apt-get install python3
* Pipenv:   sudo pip3 install pipenv
* jq:       sudo apt-get install jq
* make:     sudo apt-get install make
* check out github source (or pull release) *FIXME*

After unpacking the package, please change into the top level
directory and run `pipenv install` to install the necessary Python
packages.

If you have not already done so, please configure the AWS cli as
described here:
https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
Note that it is not recommended to use the AWS root account for actual
work. The reasoning behind that are outlined here: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#lock-away-credentials.
Instead create a separate Admin account and use its credentials for
the AWS cli configuration.

### AWS Deployment

Aside from the AWS cli configuration, you also need to provide an S3
bucket to house a transient file that is necessary for the AWS
configuration. Specifically, we will deposit a zip file there with the
backend event detection code. You can use an existing bucket in your
account or create a new one.

Unpack the release package to a suitable directory. In a shell window,
cd into the root directory and run 'pipenv install'. After that, cd
into the `aws` subdirectory.  Open the settings.sh in an editor and
provide any missing values and review the rest to make sure they are
ok for your purposes. The comments in `settings.sh` should be
sufficient to explain the purpose of each. The `PROFILE` value will be
passed as the `aws --profile` argument.

For reference I have included the settings.sh file that I am using for
my setup: `settings-ktsr42.sh`.  You will not be able to use it
though.
 
Once you are happy with the `settings.sh` file, save it to disk. Now
execute the `update_stack.sh` script from the `aws` subdirectory (your
cwd should still be this dir). This will create all necessary AWS
resources. If you change your mind about a setting in `settings.sh`, just
change it and run update_stack.sh again.

The script should block and wait until the AWS configuraton is fully
complete. It creates the configuration file for the temperature
reader, which is why it has to be run first.

### Raspberry PI Deployment

If you are stil in the `aws` subdirectory enter `cd ..` to switch back
to the distribution root. Run `make dist-reader` from the root
directory

This will create a `temp_reader-<REL>.tar.gz` archive file in the root
directory. Copy this file to the Raspberry PI and unpack it into a
`releases` subdirectory:

    $ whoami
    tsensor
    $ mkdir releases
    $ cd releases
    $ tar xzvf ~/temp_reader-<REL>.tar.gz

Create a symbolic link to point to the latest release:

    $ ln -snf temp_reader-<REL> prod

Make sure that the temperature sensor is attached to the RPI as
described in the guideline you chose to follow and that the path to
the temperature reading file under /proc comes back after a reboot.

Create a symbolic link in the home directory of tsensor to point to
the actual reading file in /proc. For testing purposes you can
point that link instead at `releases/prod/sensor.dummy`.

Install the required Python packages by running

    $ cd ~/releases/prod
    $ pipenv install

Execute the temperature reader once for testing purposes:

    ./run.sh

to ensure the reader is working. It should not produce any output. You
can verify that the reader has pushed a new file to the S3 bucket used
for capturing by executing:

    aws s3 ls gs://<your bucket from settings.sh>/observations

The reader writes its logfile to ~/logs/reader_log. Please review this
file if anything seems to be off.

If everything is good, start the regular temperature monitoring by
putting the script into cron:

    crontab releases/prod/crontab

This will run the temperature reader every 20 minutes. Feel free to
edit the crontab file (see `man 5 crontab`) if you would like to
change the frequency. Note that above a certain threshold AWS starts
to charge for traffic to S3.

