#!/bin/sh

USER_ID=${UID}
GROUP_ID=${GID}

echo "Starting Hydrus with UID/GID : $USER_ID/$GROUP_ID"

cd /opt/hydrus/

if [ -f "/opt/hydrus/static/build_files/docker/client/patch.patch" ]; then
  echo "Patching Hydrus"
  patch -f -p1 -i /opt/hydrus/static/build_files/docker/client/patch.patch
fi

if [ -f "/opt/hydrus/static/build_files/docker/client/requests.patch" ]; then
  cd /usr/lib/python3.10/site-packages/requests
    echo "Patching Requests"
    patch -f -p2 -i /opt/hydrus/static/build_files/docker/client/requests.patch
  cd /opt/hydrus/
fi

#if [ $USER_ID !=  0 ] && [ $GROUP_ID != 0 ]; then
#  find /opt/hydrus/ -not -path "/opt/hydrus/db/*" -exec chown hydrus:hydrus "{}" \;
#fi

exec supervisord -c /etc/supervisord.conf
