# Hydrus in a container(docker)

Latest hydrus client that runs in docker 24/7. Employs xvfb and vnc. Runs on alpine.

Start container: `docker run --name hydrusclient -d -p 5800:5800 -p 5900:5900 ghcr.io/hydrusnetwork/hydrus:latest`.
Connect to noVNC via `http://yourdockerhost:5800/vnc.html` or use [Tiger VNC Viewer](https://bintray.com/tigervnc/stable/download_file?file_path=vncviewer-1.9.0.exe) or any other VNC client and connect on port **5900**.

For persisten storage you can either create a named volume or mount a new/existing db path `-v /hydrus/client/db:/opt/hydrus/db`.
The client runs with default permissions of `1000:1000`, ~~this can be changed by the ENV `UID` and `GID`(not working atm, fixed to 1000)~~ will be fixed someday.

#### The container will **NOT** fix the permissions inside the db folder. **CHOWN YOUR DB FOLDER CONTENT ON YOUR OWN**

If you have enough RAM, mount `/tmp` as tmpfs. If not, download more RAM.

As of `v359` hydrus understands IPFS `nocopy`. And can be easily run with go-ipfs container.
Read [Hydrus IPFS help](https://hydrusnetwork.github.io/hydrus/help/ipfs.html). Mount `HOST_PATH_DB/client_files` to `/data/client_files` in ipfs. Go manage the ipfs service and set the path to `/data/client_files`, you'll know where to put it in.

**OR**, the compose file:
```
version: '2'
services:
  hydrusclient:
    image: ghcr.io/hydrusnetwork/hydrus:latest
    container_name: hydrusclient
    restart: unless-stopped
    environment:
      - UID=1000
      - GID=1000
    volumes:
      - HOST_PATH_DB:/opt/hydrus/db
    tmpfs:
      - /tmp #optional for SPEEEEEEEEEEEEEEEEEEEEEEEEED and less disk access
    ports:
      - 5800:5800   #noVNC
      - 5900:5900   #VNC
      - 45868:45868 #Booru
      - 45869:45869 #API
  hydrusclient-ipfs:
    image: ipfs/go-ipfs
    container_name: hydrusclient-ipfs
    restart: unless-stopped
    volumes:
      - HOST_PATH_IPFS:/data/ipfs
      - HOST_PATH_DB/client_files:/data/client_files:ro
    ports:
      - 4001:4001 # READ
      - 5001:5001 # THE
      - 8080:8080 # IPFS
      - 8081:8081 # DOCS
  hydrus-web:
    image: floogulinc/hydrus-web
    container_name: hydrus-web
    restart: always
    ports:
      - 8080:80 # READ
```
Further containerized application of interest:
- [Hybooru](https://github.com/funmaker/hybooru): [Hydrus](https://github.com/hydrusnetwork/hydrus)-based booru-styled imageboard in React, inspired by [hyve](https://github.com/mserajnik/hyve/).
- [hydownloader](https://github.com/thatfuckingbird/hydownloader): Alternative way of downloading and importing files. Decoupled from hydrus logic and limitations.

## Building
```
# Alpine (client)
cd hydrus/
docker build -t ghcr.io/hydrusnetwork/hydrus:latest -f static/build_files/docker/client/Dockerfile .
```
