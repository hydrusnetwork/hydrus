# Hydrus in a container(HiC)

Latest hydrus client that runs in docker 24/7. Employs xvfb and vnc. Runs on alpine.

TL;DR: `docker run --name hydrusclient -d -p 5800:5800 -p 5900:5900 ghcr.io/hydrusnetwork/hydrus:latest`.
Connect to noVNC via `http://yourdockerhost:5800/vnc.html` or use [Tiger VNC Viewer](https://bintray.com/tigervnc/stable/download_file?file_path=vncviewer-1.9.0.exe) or any other VNC client and connect on port **5900**.

For persistent storage you can either create a named volume or mount a new/existing db path `-v /hydrus/client/db:/opt/hydrus/db`.
The client runs with default permissions of `1000:1000`, ~~this can be changed by the ENV `UID` and `GID`(not working atm, fixed to 1000)~~ will be fixed someday™.

#### The container will **NOT** fix the permissions inside the db folder. **CHOWN YOUR DB FOLDER CONTENT ON YOUR OWN**

If you have enough RAM, mount `/tmp` as tmpfs. If not, download more RAM.

As of `v359` hydrus understands IPFS `nocopy`. And can be easily run with go-ipfs container.
Read [Hydrus IPFS help](https://hydrusnetwork.github.io/hydrus/help/ipfs.html). Mount `HOST_PATH_DB/client_files` to `/data/client_files` in ipfs. Go manage the ipfs service and set the path to `/data/client_files`, you'll know where to put it in.

Example compose file:
```yml
version: '3.8'
volumes:
  tor-config:
    driver: local
  hybooru-pg-data:
    driver: local
  hydrus-server:
    driver: local
  hydrus-client:
    driver: local
  ipfs-data:
    driver: local
  hydownloader-data:
    driver: local
services:
  hydrusclient:
    image: ghcr.io/hydrusnetwork/hydrus:latest
    container_name: hydrusclient
    restart: unless-stopped
    environment:
      - UID=1000
      - GID=1000
    volumes:
      - hydrus-client:/opt/hydrus/db
    tmpfs:
      - /tmp #optional for SPEEEEEEEEEEEEEEEEEEEEEEEEED and less disk access
    ports:
      - 5800:5800   #noVNC
      - 5900:5900   #VNC
      - 45868:45868 #Booru
      - 45869:45869 #API

  hydrusserver:
    image: ghcr.io/hydrusnetwork/hydrus:server
    container_name: hydrusserver
    restart: unless-stopped
    volumes:
      - hydrus-server:/opt/hydrus/db

  hydrusclient-ipfs:
    image: ipfs/go-ipfs
    container_name: hydrusclient-ipfs
    restart: unless-stopped
    volumes:
      - ipfs-data:/data/ipfs
      - hydrus-clients:/data/db:ro
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

  hybooru-pg:
    image: healthcheck/postgres
    container_name: hybooru-pg
    environment:
      - POSTGRES_USER=hybooru
      - POSTGRES_PASSWORD=hybooru
      - POSTGRES_DB=hybooru
    volumes:
      - hybooru-pg-data:/var/lib/postgresql/data
    restart: unless-stopped

  hybooru:
    image: suika/hybooru:latest # https://github.com/funmaker/hybooru build it yourself
    container_name: hybooru
    restart: unless-stopped
    depends_on:
      hybooru-pg:
        condition: service_started
    ports:
      - 8081:80 # READ
    volumes:
      - hydrus-client:/opt/hydrus/db

  hydownloader:
    image: ghcr.io/thatfuckingbird/hydownloader:edge
    container_name: hydownloader
    restart: unless-stopped
    ports:
      - 53211:53211
    volumes:
      - hydownloader-data:/db
      - hydrus-client:/hydb

  tor-socks-proxy:
    #network_mode: "container:myvpn_container" # in case you have a vpn container
    container_name: tor-socks-proxy
    image: peterdavehello/tor-socks-proxy:latest
    restart: unless-stopped

  tor-hydrus:
    image: goldy/tor-hidden-service
    container_name: tor-hydrus
    depends_on:
      hydrusclient:
        condition: service_healthy
      hydrusserver:
        condition: service_healthy
      hybooru:
        condition: service_started
    environment:
        HYBOORU_TOR_SERVICE_HOSTS: '80:hybooru:80'
        HYBOORU_TOR_SERVICE_VERSION: '3'
        HYSERV_TOR_SERVICE_HOSTS: 45870:hydrusserver:45870,45871:hydrusserver:45871
        HYSERV_TOR_SERVICE_VERSION: '3'
        HYCLNT_TOR_SERVICE_HOSTS: 45868:hydrusclient:45868,45869:hydrusclient:45869
        HYCLNT_TOR_SERVICE_VERSION: '3'
    volumes:
      - tor-config:/var/lib/tor/hidden_service 
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
