FROM ghcr.io/suika/opencv-video-minimal:4.5-py3.8

ARG UID
ARG GID

HEALTHCHECK --interval=20s --timeout=10s --retries=3 --start-period=30s CMD ! supervisorctl status | grep -v RUNNING
ENTRYPOINT ["/bin/sh", "/opt/hydrus/static/build_files/docker/client/entrypoint.sh"]
LABEL git="https://github.com/hydrusnetwork/hydrus"

RUN apk --no-cache add jq fvwm x11vnc xvfb supervisor py3-beautifulsoup4 py3-psutil py3-pysocks py3-requests py3-twisted py3-yaml qt5-qtcharts py3-lz4 ffmpeg  py3-pillow py3-numpy py3-numpy py3-qt5 py3-openssl openssl mpv mpv-libs nodejs patch \
 && apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/community font-noto font-noto-emoji \
 && apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/community font-noto-cjk
RUN pip install qtpy Send2Trash html5lib twisted python-mpv cloudscrape cloudscraper pyparsing

RUN set -xe \
    && mkdir -p /opt/hydrus \
    && addgroup -g 1000 hydrus \
    && adduser -h /opt/hydrus -u 1000 -H -S -G hydrus hydrus

RUN mkdir -p /opt/noVNC/utils/websockify \
 && wget $(wget https://api.github.com/repos/novnc/noVNC/releases/latest -qO- | jq  -r '.tarball_url') -qO- | tar xzf - --strip-components=1 -C /opt/noVNC \
 && wget $(wget https://api.github.com/repos/novnc/websockify/releases/latest -qO- | jq  -r '.tarball_url') -qO- | tar xzf - --strip-components=1 -C /opt/noVNC/utils/websockify \
 && sed -i -- "s/ps -p/ps -o pid | grep/g" /opt/noVNC/utils/launch.sh \
 && chown hydrus:hydrus -R /opt/noVNC

COPY --chown=hydrus . /opt/hydrus
COPY --chown=hydrus --from=suika/swftools:2013-04-09-1007 /swftools/swfrender /opt/hydrus/bin/swfrender_linux

RUN mv /opt/hydrus/static/build_files/docker/client/supervisord.conf /etc/supervisord.conf && \
    mv /opt/hydrus/static/build_files/docker/client/novnc/index.html /opt/noVNC/index.html && \
    mv /opt/hydrus/static/build_files/docker/client/novnc/icon.png /opt/noVNC/app/images/icons/icon.png

RUN ln -fs /usr/bin/python3 /usr/bin/python && ln -fs /usr/bin/pip3 /usr/bin/pip

VOLUME /opt/hydrus/db

ENV QT_SCALE_FACTOR=1.1 \
    VNC_PORT=5900 \
    NOVNC_PORT=5800 \
    SUPERVISOR_PORT=9001 \
    XVFBRES=1680x1050x24 \
    UID=${UID:-1000} \
    GID=${GID:-1000} \
    DB_DIR=/opt/hydrus/db \
    XVFB_EXTRA="" \
    VNC_EXTRA="" \
    NOVNC_EXTRA="" \
    HYDRUS_EXTRA=""

EXPOSE 5800 5900
