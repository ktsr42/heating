import argparse
import datetime
import sys

import boto3

Funcname='ktsr42_lambda_test2'
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
    streams = cwlogs.describe_log_streams(logGroupName = logGroupName, orderBy='LastEventTime', descending=True)['logStreams']
    for s in streams:
        print("{}, created {}, lastEvent {}".format(s['logStreamName'], print_aws_timestamp(s['creationTime']), print_aws_timestamp(s['lastEventTimestamp'])))

if __name__ == '__main__':
    main()
    
