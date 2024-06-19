#!/bin/sh

USER_ID=${UID}
GROUP_ID=${GID}

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)

#apk add xterm
echo "Starting Hydrus with UID/GID : $USER_ID/$GROUP_ID"

cd /opt/hydrus/

if [ -f "/opt/hydrus/static/build_files/docker/client/patch.patch" ]; then
  echo "Patching Hydrus"
  patch -f -p1 -i /opt/hydrus/static/build_files/docker/client/patch.patch
fi

# Determine which requests patch file to use and warn on unsupported python version
if [ "$PYTHON_MAJOR_VERSION" == "3" ]; then
  if [ "$PYTHON_MINOR_VERSION" -lt 11 ]; then
    PATCH_FILE="/opt/hydrus/static/build_files/docker/client/requests.patch"
    if [ -f "$PATCH_FILE" ]; then
      echo "Found and apply requests patch for py 3.10 and below"
      cd $(python3 -c "import sys; import requests; print(requests.__path__[0])")
      patch -f -p2 -i "$PATCH_FILE"
    fi
  elif [ "$PYTHON_MINOR_VERSION" -eq 11 ]; then
    PATCH_FILE="/opt/hydrus/static/build_files/docker/client/requests.311.patch"
    if [ -f "$PATCH_FILE" ]; then
      echo "Found and apply requests patch for py 3.11"
      cd $(python3 -c "import sys; import requests; print(requests.__path__[0])")
      patch -f -i "$PATCH_FILE"
    fi
  else
    echo "Unsupported Python minor version: $PYTHON_MINOR_VERSION"
  fi
else
  echo "Unsupported Python major version: $PYTHON_MAJOR_VERSION"
fi
cd /opt/hydrus/

#if [ $USER_ID !=  0 ] && [ $GROUP_ID != 0 ]; then
#  find /opt/hydrus/ -not -path "/opt/hydrus/db/*" -exec chown hydrus:hydrus "{}" \;
#fi

exec supervisord -c /etc/supervisord.conf
