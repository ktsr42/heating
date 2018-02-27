from __future__ import print_function

import json
import urllib.parse
import boto3

print('Loading function')

s3 = boto3.client('s3')
# sns = boto3.client('sns')


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    print('context: {}'.format(context))
    try:
        if 'Records' in event:
            for rec in event['Records']:
                if rec.get('eventSource','') == 'aws:s3':
                    print('Received s3 event')
                    bucket = rec['s3']['bucket']['name']
                    key = urllib.parse.unquote_plus(rec['s3']['object']['key'])
                    obj = s3.get_object(Bucket = bucket, Key = key)
                    print('Object s3://{}/{}, type {}'.format(bucket,key, obj['ContentType']))
                    # sns.publish(PhoneNumber='+15515802081', Message='AWS Lambda saw a new upload: ' + key)
        elif event.get('source', '') == 'aws.events':
            print('Received scheduled event, time {}, resource {}'.format(event['time'], event['resources'][0]))
        else:
            print("Received unexpected event, ignoring")
        return
    except Exception as e:
        print(e)
        raise e
