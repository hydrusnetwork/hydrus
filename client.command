#!/bin/bash

if [ ! -d "venv" ]; then
	echo "You need to set up a venv! Check the running from source help for more info!"
	exit 1
fi

source venv/bin/activate

# You can copy this file to 'client-user.sh' and add in your own launch parameters here if you like, and a git pull won't overwrite the file.
# Just tack new params on like this:
# python client.py -d="/path/to/hydrus/db"

python client.py

deactivate
