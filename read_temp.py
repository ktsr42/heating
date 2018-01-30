import argparse
import configparser
import datetime
import json
import os
import pathlib
import sys
import time

import botocore.config as awsconfig
import boto3


TemperatureSensorFile="/sys/bus/w1/devices/<serial>/w1_slave"
History="temperature_history"
ReadingFilePrefix="pipe_temperature."
MaxReadings = 100
AwsParameters = ('region', 'key_id', 'secret_key', 'bucket', 'path', 'prefix')

def read_current_temperature(srcfile):
    with open(srcfile) as tf:
        data = tf.read()
    temperature_reading_line = data.split('\n')[1]
    (_, tag, temperature_reading) = temperature_reading_line.partition('t=')
    if tag != 't=':
        raise Exception('Could not parse temperature sensor file')
    return (time.time(), int(temperature_reading) / 1000)

def get_last_reading_number(targetdir, prefix):
    old_readings = [int(f[len(prefix):]) for f in os.listdir(targetdir) if f[:len(prefix)] == prefix]
    if len(old_readings) == 0:
        return 0
    else:
        return max(old_readings)

def order(n0):
    if n0 == 0:
        return 0
    o = -1
    n = n0
    while n > 0:
        o += 1
        n = n // 10
    return o

def write_reading(targetdir, prefix, reading):
    num = (get_last_reading_number(targetdir, prefix) + 1) % MaxReadings
    fname = "{0}/{1}{3:0{2}}".format(History, ReadingFilePrefix, order(MaxReadings), num)
    with open(fname, "w") as f:
        print("{0} {1}".format(time.time(), reading), file=f)
    
def create_aws_message(srcdir, prefix):
    sdir = pathlib.Path(srcdir)
    allreadings_t = [e.read_text().strip().split() for e in sdir.iterdir() if e.is_file() and e.name[:len(prefix)] == prefix]
    kf = lambda x: x[0]
    return json.dumps(sorted(((int(ts), r) for ts, r in allreadings_t), key = kf))

def aws_upload(params, data, suffix=".json"):
    fname = "{}/{}{:%Y%m%dT%H%m%S}{}".format(params.path, params.prefix, datetime.datetime.utcnow(), suffix)
    config = awsconfig.Config(region_name=params.region)
    s3 = boto3.resource(service_name = 's3', aws_access_key_id = params.key_id, aws_secret_access_key = params.secret_key, config=config)
    s3obj = s3.Object(params.bucket, fname)
    s3obj.put(Body=data.encode())

def read_config(fname):
    config = configparser.Parser()
    config.read(fname)
    args = argparse.Namespace()
    sect_input = config['Input']
    args.sensorfile = sect_input['Sensorfile']
    args.local_history = sect_input['HistoryDir']
    args.local_file_prefix = sect_input['FilePrefix']
    args.max_readings = sect_input['MaxReadings']
    aws_params = argparse.Namespace()
    for k in AwsParameters:
        aws_params.__setattr__[k] = config['AWS'][k]
    args.aws_params = aws_params
    secret_key = pathlib.Path(aws_params.secret_key).read_bytes()
    aws_params.secret_key = secret_key
    return args
    
def main():
    # read config file
    params = read_config(sys.argv[1])
    
    # read temperature
    print("Reading the current temperature...")
    reading = read_current_temperator(params.sensorfile)
    print("Current temperature is {}".format(reading))
    
    # write locally
    write_reading(args.local_history, args.local_file_prefix, reading)
    
    # create aws s3 object contents
    print("Create AWS file")
    aws_msg = create_aws_message(args.local_history, args.local_file_prefix)
    
    # upload to s3
    print("Uploading to aWs S3")
    aws_upload(args.aws_params, aws_msg)
    print("Data uploaded successfully, exiting.")

if __name__ == '__main__':
    main()
