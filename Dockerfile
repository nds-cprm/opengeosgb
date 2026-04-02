FROM geonode/geonode-base:latest-ubuntu-24.04

# https://specs.opencontainers.org/image-spec/annotations/
LABEL org.opencontainers.image.title="OpenGeoSGB/GeoNode" \
    org.opencontainers.image.version="5.0.2" \
    org.opencontainers.image.authors="GeoNode development team & NDS CPRM"    

RUN apt-get update -y && \
    apt-get -y --no-install-recommends --no-install-suggests install \
        curl wget unzip gnupg2 locales && \
    apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

WORKDIR /usr/src/project

COPY src/tasks.py \
    src/entrypoint.sh \
    src/requirements.txt \
    /usr/src/project/

COPY src/wait-for-databases.sh /usr/bin/wait-for-databases

COPY src/celery.sh /usr/bin/celery-commands

COPY src/celery-cmd /usr/bin/celery-cmd

RUN chmod +x /usr/bin/wait-for-databases \
        /usr/src/project/tasks.py \ 
        /usr/src/project/entrypoint.sh \
        /usr/bin/celery-commands \
        /usr/bin/celery-cmd && \
    python -m pip install -U pip setuptools wheel && \
    pip install --src /usr/src -r requirements.txt

COPY src/ /usr/src/project

RUN yes w | pip install -e .

RUN mkdir -p /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode && \
    chmod g=u /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode
EXPOSE 8000
