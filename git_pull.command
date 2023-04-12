#!/bin/bash

pushd "$(dirname "$0")" || exit 1

git pull

echo "Done!"

read -r

popd || exit
