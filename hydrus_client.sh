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

# You can copy this file to 'hydrus_client-user.sh' and add in your own launch parameters here if you like. A git pull won't overwrite that filename.
# Just tack new hardcoded params on like this:
#
# python hydrus_client.py -d="/path/to/hydrus/db" "$@"
#
# The "$@" part also passes on any launch parameters this script was called with, so you can also just go--
#
# ./hydrus_client.sh -d="/path/to/hydrus/db"
#
# --depending on your needs!
#
# Also, if you need to put environment variables in this script, do it like this (before the program is booted!):
#
# export QT_QPA_PLATFORM=xcb
# export WAYLAND_DISPLAY=
#
# To unset an env, do this:
#
# unset WAYLAND_DISPLAY

python hydrus_client.py "$@"

deactivate

popd || exit
