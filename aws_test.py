import read_temp
import json
import argparse

def run():
    params = argparse.Namespace()
    params.bucket = 'heating.ktsr42.s3'
    params.key_id = 'AKIAJLRLC2ZP7IR37QIA'
    params.secret_key = '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'
    params.region = 'us-east-1'
    params.path = 'readings'
    params.prefix = 'prefix'
    data = dict(x='lolo', y=42)
    read_temp.aws_upload(params, json.dumps(data))

if __name__ == '__main__':
    run()
