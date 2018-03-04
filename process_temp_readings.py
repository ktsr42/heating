# status:
# - last message timestamp
# - last message temperature
# - last alert timestamp

# read status
# if event == s3 put object
#   parse message
#   write consolidated data (allreadings/YYYYMMDD.json)
#   if most recent temperature < config['min_temp'] and last_alert_timestamp - now > config['min_alert_gap']
#     send_temperature_alert
# if event = scheduled event
#   if last message timestamp - now > config['max_message_gap']:
#     send_no_readings_alert
# write status file

# catch exceptions and send alert

import argparse
import datetime
import json
import sys
import time
import urllib.parse

import boto3
import botocore.errorfactory

ConfigFile = 'lambda_internal/config.json'
LambdaStatus = 'lambda_internal/status.json'

ConfigKeys = dict(minimum_temperature = float, repeat_alert_hours = int, phonenumber = str, max_delay = lambda v: int(v) * 60)

def read_config(xenv):
    class D(): pass
    cfg = D()
    rawvals = json.load(xenv.s3.get_object(Bucket = xenv.lambda_bucket, Key = ConfigFile)['Body'])
    for k in ConfigKeys.keys():
        cfg.__setattr__(k, ConfigKeys[k](rawvals[k]))
    return cfg


class Status():
    def __init__(self, temp_reading = 0, last_reading_ts = 0, last_alert_ts = 0):
        self.temp_reading = temp_reading
        self.last_reading_ts = last_reading_ts
        self.last_alert_ts = last_alert_ts

    def create_json(self):
        values = dict(temperature_reading = self.temp_reading,
                      last_reading_timestamp = self.last_reading_ts,
                      last_alert_timestamp = self.last_alert_ts)
        return json.dumps(values)

    @staticmethod
    def read_status(file):
        values = json.load(file)
        args = [float(values.get(k, 0)) for k in ('temperature_reading', 'last_reading_timestamp', 'last_alert_timestamp')]
        return Status(*args)

                 
def write_readings(xenv, bucket, readings):
    now = time.time()
    datemaps = dict()
    for r in readings:
        r['received'] = now
        rd = datetime.date.fromtimestamp(r['timestamp'])
        l = datemaps.get(rd, [])
        l.append(r)
        datemaps[rd] = l

    for dt in datemaps.keys():
        fname = dt.strftime('allreadings/day%Y%m%d.json')
        try:
            datereadings = json.load(xenv.s3.get_object(Bucket = bucket, Key = fname)['Body'])
        except botocore.errorfactory.ClientError:
            datereadings = []
        datereadings.extend(datemaps[dt])
        sortedreadings = sorted(datereadings, key = lambda x:x['timestamp'])
        xenv.s3.put_object(Bucket = bucket, Key=fname, Body = json.dumps(sortedreadings).encode())

def consolidate_readings(readings):
    assert len(readings) > 0
    sorted_readings = sorted(readings, key = lambda x:x['timestamp'])
    if len(readings) == 1:
        unique_indices = [0]
    else:
        unique_indices = [0] + [i for i in range(1, len(sorted_readings)) if sorted_readings[i]['timestamp'] != sorted_readings[i-1]['timestamp']]
    return [sorted_readings[i] for i in unique_indices]

def send_alert(xenv, msg):
    xenv.get_sns_client().publish(Phonenumber=xenv.config.phonenumber, Message=msg)
    
def process_temperature_reading(xenv, records):
    latest_reading = dict(timestamp = 0)
    all_readings = []
    now = time.time()
    for rec in records:
        if rec.get('eventSource', '') != 'aws:s3':
            print("Unknown event record: " + json.dumps(record, indent=2))
            continue
        bucket = rec['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(rec['s3']['object']['key'])
        obj = xenv.s3.get_object(Bucket = bucket, Key = key)
        readings = [dict(timestamp = float(d['timestamp']), temperature = float(d['temperature'])) for d in json.load(obj['Body'])]
        all_readings.extend(readings)

    if len(all_readings) == 0:
        send_alert(xenv, "Lambda event handler was invoked, but no temperature readings were processed.")
        return Status(0,0,now)

    cons_readings = consolidate_readings(all_readings)
    write_readings(xenv, bucket, cons_readings)
        
    latest_reading = cons_readings[-1]

    temperature,timestamp = [latest_reading[k] for k in ('temperature','timestamp')]
    if temperature < xenv.config.minimum_temperature:
        if timestamp > last_status.last_alert_ts + 3600 * xenv.config.repeat_alert_hours:
            ts = datetime.datetime.fromtimestamp(timestamp)
            msg = "The latest temperature reading of {} (as of {%Y.%m.%d %H:%M:%S}) has fallen below the threshold of {}".format(temperature, ts, config['minimum_temperature'])
            send_alert(xenv, msg)
            return Status(temperature, timestamp, now)
    delay = now - timestamp
    if xenv.config.max_delay < delay:
        send_alert(xenv, "Warning, received a delayed temperature reading. Delay is {}".format(datetime.timedelta(seconds=int(delay))))
        return Status(temperature, timestamp, now)
    
    return Status(temperature, timestamp, last_status.last_alert_ts)


def process_scheduled_event(xenv, event):
    if xenv.last_status.last_reading_ts == 0:
        return xenv.last_status
    now = time.time()
    delay = now - xenv.last_status.last_reading_ts
    if xenv.config.max_delay < delay:
        send_alert(xenv, "Failed to receive temperature readings for {}".format(datetime.timedelta(seconds=int(delay))))
        return Status(xenv.last_status.temp_reading, xenv.last_status.last_reading_ts, now)
    return xenv.last_status
    

def process_events(xenv, event, context):
    xenv.config = read_config(xenv)
    try:
        xenv.last_status = Status.read_status(xenv.s3.get_object(Bucket = xenv.lambda_bucket, Key = LambdaStatus)['Body'])
    except botocore.errorfactory.ClientError:
        xenv.last_status = Status()
    
    if 'Records' in event:
        new_status = process_temperature_reading(xenv, event['Records'])
    elif event.get('source', '') == 'aws.events':
        new_status = process_scheduled_event(xenv, event)
    else:
        send_alert(xenv, "Lambda function received an unexpected event.")
        print(json.dumps(event, indent=2))
        new_status = Status(last_status.temp_reading, last_status.last_reading_ts, time.time())
    xenv.s3.put_object(Bucket = xenv.lambda_bucket, Key = LambdaStatus, Body = new_status.create_json().encode())


# differences between local and lamdba env:
# * access s3 using key
# * no sms (at least initially)

class ExecutionEnvironment():
    pass

def init_lambda():
    xenv = ExecutionEnvironment()
    xenv.s3 = boto.client('s3')
    xenv.lambda_bucket = os.getenv('CONFIG_BUCKET')
    xenv.get_sns_client = lambda: boto.client('sns')
    return xenv
    

def lambda_handler(event, context):
    try:
        process_events(init_lambda(), event, context)
    except Exception as e:
        print('Exception while processing event:')
        print(e)
        
def init_local(profile, bucket):
    xenv = ExecutionEnvironment()
    xenv.s3 = boto3.Session(profile_name = profile).client('s3')
    class MockSns():
        def publish(self, Phonenumber, Message):
            print('SNS message to {}: "{}"'.format(Phonenumber, Message))
    xenv.lambda_bucket = bucket
    xenv.get_sns_client = lambda: MockSns()
    return xenv

def parse_commandline(cmdline):
    # --profile <profile> file|schedule --bucket <bucket> --file filekey1 --file filekey2
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', default='default', help='Which aws profile to use')
    parser.add_argument('--bucket', default='ktsr42.s3.heating', help='Which bucket to use for putfile events')
    parser.add_argument('event', choices=['file', 'schedule'], help = 'Type of event to feed to the handler')
    parser.add_argument('--file', nargs='*', default = [], help = 'Filename to put into a putfile event (may be repeated)')
    args = parser.parse_args(cmdline)
    if args.event == 'file':
        if args.file == []:
            parser.error('For file events you must supply at least one --file argument')
    return args

def main():
    args = parse_commandline(sys.argv[1:])
    xenv = init_local(args.profile, args.bucket)
    if args.event == 'schedule':
        event = dict(source = 'aws.events')
    else:
        records = [dict(eventSource = 'aws:s3', s3 = dict(bucket=dict(name=args.bucket), object=dict(key=f))) for f in args.file]
        event = dict(Records=records)
    
    process_events(xenv, event, None)

if __name__ == '__main__':
    main()
    
