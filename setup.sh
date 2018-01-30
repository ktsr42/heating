#!/bin/bash

HEATING=$(cd "$(dirname $BASH_SOURCE[0])" && pwd)
export HEATING

# Set PYTHONPATH to include bin
export PYTHONPATH="$PYTHONPATH:$HEATING"
