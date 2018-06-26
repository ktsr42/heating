#!/bin/bash

cd "$(dirname $BASH_SOURCE[0])"

pipenv run python read_temp.py read_temp_config.ini

