# heating

Monitor a temperature sensor via AWS (lambda + S3)

# Install

## work machine (Linux)
* Python 3
* Pipenv
* jq
* check out github source (or download release)

## Raspberry PI
* Python 3
* Attach temperature sensor (find link)

# Procedure
* On work machine, go to ./aws
* Edit settings.sh
* Edit receiver_config.yaml (change phone number) - temperatures are in Celsius, max_delay is minutes
* Run update_stack.sh
* cd ..
* run make dist-reader
* scp temp_reader-....tar.gz to RPI
* ssh to RPI
* create the application user set in settings.sh
* as that user, install temp_reader-release-X.XX.tar.gz
* create prod symlink
* install pipenv as root
* run pipenv 
* run temp_reader once
* Load crontab
 
