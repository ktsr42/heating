import argparse
import datetime
import sys

import boto3

Funcname='ktsr42_heating_lambda'
Profile="root"

def print_aws_timestamp(awsts):
    return datetime.datetime.fromtimestamp(int(awsts) / 1000).strftime("%Y.%m.%dD%H:%M:%S.%f")

def parse_commandline(cmdline):
    parser = argparse.ArgumentParser("List AWS Lambda event logs from AWS Cloudwatch")
    parser.add_argument("--profile", type=str, default="default", help="Which AWS setup profile to use")
    parser.add_argument("funcname", type=str, help="Which Lambda function to dump the log for")
    return parser.parse_args(cmdline)

def main():
    args = parse_commandline(sys.argv[1:])
    session = boto3.Session(profile_name = args.profile)
    cwlogs = session.client('logs')
    logGroupName ='/aws/lambda/' + args.funcname
    lastlog = cwlogs.describe_log_streams(logGroupName = logGroupName, orderBy='LastEventTime', descending=True)['logStreams'][0]
    logStreamName = lastlog['logStreamName']
    log = cwlogs.get_log_events(logGroupName=logGroupName, logStreamName = logStreamName)['events']
    print("Dumping {}, created on {}".format(logStreamName, print_aws_timestamp(lastlog['creationTime'])))
    for event in log:
        print("{}: {}".format(print_aws_timestamp(event['timestamp']), event['message'].rstrip()))

if __name__ == '__main__':
    main()
    
