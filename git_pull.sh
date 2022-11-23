#!/bin/bash

pushd "$(dirname "$0")"

git pull

echo "Done!"

popd
