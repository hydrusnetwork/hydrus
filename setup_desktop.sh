#!/bin/bash

pushd "$(dirname "$0")" || exit 1

INSTALL_DIR="$(readlink -f .)"
DESKTOP_SOURCE_PATH=$INSTALL_DIR/static/hydrus.desktop
DESKTOP_DEST_PATH=$HOME/.local/share/applications/hydrus.desktop

echo "Install folder appears to be $INSTALL_DIR"

if [ ! -f "$DESKTOP_SOURCE_PATH" ]; then
    echo "Sorry, I do not see the template file at $DESKTOP_SOURCE_PATH! Was it deleted, or this script moved?"
    popd || exit 1
    exit 1
fi

if [ -f "$DESKTOP_DEST_PATH" ]; then

    echo "You already have a hydrus.desktop file at $DESKTOP_DEST_PATH. Would you like to overwrite it? y/n "

else

    echo "Create a hydrus.desktop file at $DESKTOP_DEST_PATH? y/n "

fi

read -r affirm

if [ "$affirm" = "y" ]; then
    :
elif [ "$affirm" = "n" ]; then
    popd || exit
    exit 0
else
    echo "Sorry, did not understand that input!"
    popd || exit 1
    exit 1
fi

sed -e "s#Exec=.*#Exec=${INSTALL_DIR}/hydrus_client.sh#" -e "s#Icon=.*#Icon=${INSTALL_DIR}/static/hydrus.png#" "$DESKTOP_SOURCE_PATH" > "$DESKTOP_DEST_PATH"

echo "Done!"

popd || exit
