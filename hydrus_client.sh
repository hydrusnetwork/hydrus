#!/bin/bash

pushd "$(dirname "$0")" || exit 1

if [ ! -d "venv" ]; then
    echo "You need to set up a venv! Check the running from source help for more info!"
    popd || exit 1
    exit 1
fi

if ! source venv/bin/activate; then
    echo "The venv failed to activate, stopping now!"
    popd || exit 1
    exit 1
fi

# You can copy this file to 'client-user.sh' and add in your own launch parameters here if you like, and a git pull won't overwrite the file.
# Just tack new params on like this:
# python hydrus_client.py -d="/path/to/hydrus/db"

python hydrus_client.py

deactivate

popd || exit
