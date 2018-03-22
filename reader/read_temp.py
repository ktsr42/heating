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


AwsParameters = ('region', 'key_file', 'bucket', 'path', 'prefix')

def read_current_temperature(srcfile):
    with open(srcfile) as tf:
        data = tf.read()
    temperature_reading_line = data.split('\n')[1]
    (_, tag, temperature_reading) = temperature_reading_line.partition('t=')
    if tag != 't=':
        raise Exception('Could not parse temperature sensor file')
    return (int(time.time()), int(temperature_reading) / 1000)

def get_last_reading_number(targetdir, prefix):
    try:
        old_readings = sorted((f for f in pathlib.Path(targetdir).iterdir() if f.name[:len(prefix)] == prefix), key=lambda f:f.stat().st_mtime, reverse=True)        
        return int(old_readings[0].name[len(prefix):])
    except IndexError:
        return -1

def order(n0):
    if n0 == 0:
        return 0
    o = -1
    n = n0
    while n > 0:
        o += 1
        n = n // 10
    return o

def write_reading(targetdir, prefix, maxreadings, reading):
    num = (get_last_reading_number(targetdir, prefix) + 1) % maxreadings
    fname = "{0}/{1}{3:0{2}}".format(targetdir, prefix, 1 + order(maxreadings), num)
    with open(fname, "w") as f:
        print("{0} {1}".format(*reading), file=f)
    
def create_aws_message(srcdir, prefix):
    sdir = pathlib.Path(srcdir)
    allreadings_t = [e.read_text().strip().split() for e in sdir.iterdir() if e.is_file() and e.name[:len(prefix)] == prefix]
    kf = lambda x: x['timestamp']
    return json.dumps(sorted((dict(timestamp=int(ts), temperature=float(r)) for ts, r in allreadings_t), key = kf), indent=2)

def aws_upload(params, data, suffix=".json"):
    fname = "{}/{}{:%Y%m%dT%H%m%S}{}".format(params.path, params.prefix, datetime.datetime.utcnow(), suffix)
    config = awsconfig.Config(region_name=params.region)
    s3 = boto3.resource(service_name = 's3', aws_access_key_id = params.key_id, aws_secret_access_key = params.secret_key, config=config)
    s3obj = s3.Object(params.bucket, fname)
    s3obj.put(Body=data.encode())

def read_config(fname):
    config = configparser.ConfigParser()
    config.read(fname)
    args = argparse.Namespace()
    sect_input = config['Input']
    args.sensorfile = sect_input['Sensorfile']
    args.local_history = sect_input['HistoryDir']
    args.local_file_prefix = sect_input['FilePrefix']
    args.max_readings = int(sect_input['MaxReadings'])
    aws_params = argparse.Namespace(key_id = None, secret_key = None, **{k:config['AWS'][k] for k in AwsParameters})
    keyfile = json.load(open(aws_params.key_file))
    aws_params.key_id = keyfile['AccessKey']['AccessKeyId']
    aws_params.secret_key = keyfile['AccessKey']['SecretAccessKey']
    args.aws_params = aws_params
    return args
    
def main():
    # read config file
    params = read_config(sys.argv[1])
    
    # read temperature
    print("Reading the current temperature...")
    reading = read_current_temperature(params.sensorfile)
    print("Current temperature is {}".format(reading))
    
    # write locally
    write_reading(params.local_history, params.local_file_prefix, params.max_readings, reading)
    
    # create aws s3 object contents
    print("Create AWS file")
    aws_msg = create_aws_message(params.local_history, params.local_file_prefix)
    
    # upload to s3
    print("Uploading to S3")
    aws_upload(params.aws_params, aws_msg)
    print("Data uploaded successfully, exiting.")

if __name__ == '__main__':
    main()
