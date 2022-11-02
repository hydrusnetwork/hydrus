#!/bin/bash

if [ -d "venv" ]; then
	echo "Virtual environment will be reinstalled. Hit Enter to start."
	read
	echo "Deleting old venv..."
	rm -rf venv
else
	echo "If you do not know what this is, check the 'running from source' help. Hit Enter to start."
	read
fi

echo "Creating new venv..."
python -m venv venv

source venv/bin/activate

python -m pip install --upgrade pip

pip3 install --upgrade wheel

pip3 install -r requirements.txt

deactivate

echo "Done!"

read
