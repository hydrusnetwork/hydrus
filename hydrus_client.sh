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

# You can add your own launch parameters here if you like this:
# ./hydrus_client.sh -d="/path/to/hydrus/db"

python hydrus_client.py "$@"

deactivate

popd || exit
