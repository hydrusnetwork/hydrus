FROM alpine:3.19

ARG UID
ARG GID

RUN apk --no-cache add py3-psutil py3-requests py3-twisted py3-yaml py3-lz4 ffmpeg py3-pillow py3-numpy py3-openssl py3-cryptography py3-service_identity py3-opencv py3-pip py3-twisted openssl su-exec
RUN pip install --break-system-packages Send2Trash

RUN set -xe \
    && mkdir -p /opt/hydrus \
    && addgroup -g 1000 hydrus \
    && adduser -h /opt/hydrus -u 1000 -H -S -G hydrus hydrus

COPY --chown=hydrus . /opt/hydrus
COPY --chown=hydrus --from=suika/swftools:2013-04-09-1007 /swftools/swfrender /opt/hydrus/bin/swfrender_linux

VOLUME /opt/hydrus/db

ENV UID=${UID:-1000} \
    GID=${GID:-1000} \
    MGMT_PORT=45870

EXPOSE ${MGMT_PORT}

ENTRYPOINT ["/bin/sh", "/opt/hydrus/static/build_files/docker/server/entrypoint.sh"]

HEALTHCHECK --interval=1m --timeout=10s --retries=3 --start-period=10s \
  CMD wget --quiet --tries=1 --no-check-certificate --spider \
    https://localhost:${MGMT_PORT} || exit 1
