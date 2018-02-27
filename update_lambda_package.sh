#!/bin/bash

zip nx.zip lambda_function.py
# aws --profile root s3 cp nx.zip s3://ktsr42.s3.code/code/
# aws --profile root lambda update-function-code --s3-bucket ktsr42.s3.code --s3-key code/nx.zip --function-name ktsr42_lambda_test2
aws --profile root lambda update-function-code --zip-file fileb://nx.zip --function-name ktsr42_lambda_test2
