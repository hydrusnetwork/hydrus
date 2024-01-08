#!/bin/bash

pushd "$(dirname "$0")" || exit 1

if [ ! -d "venv" ]; then
	echo "You need to set up a venv! Check the running from source help for more info!"
	popd || exit 1
	exit 1
fi

if [ -d "help" ]; then
	echo "Deleting old help..."
	rm -rf help
fi

echo "Creating new help..."

source venv/bin/activate

pip install mkdocs-material

mkdocs build -d help

deactivate

echo "Done!"

popd || exit
