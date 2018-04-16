#!/bin/bash

set -eu
set -o pipefail

if [[ -z "$1" ]]
then
    echo "Missing lamdba function name."
    ext 1
fi

logGroupName="/aws/lambda/$1"

maxTS=$((1000 * $(date +%s) - 86400))
while aws --profile root logs describe-log-streams --log-group-name "$logGroupName" \
	| jq ".logStreams | .[] | select(.storedBytes == 0) | select(.lastEventTimestamp < $maxTS) | .logStreamName" \
	| read lsn
do
    echo "Deleting logstream $logGroupName/$lsn"
    aws --profile root logs delete-log-stream --log-group-name "$logGroupName" --log-stream-name "$lsn"
done
