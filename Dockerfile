FROM --platform=$TARGETPLATFORM geonode/geonode-base:latest-ubuntu-24.04

# https://specs.opencontainers.org/image-spec/annotations/
LABEL org.opencontainers.image.title="OpenGeoSGB/GeoNode" \
    org.opencontainers.image.version="dev" \
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

COPY src/requirements.txt /usr/src/project/

# 755 (e não só +x): scripts precisam de leitura para rodar com um usuário que não é root
COPY --chmod=755 src/wait-for-databases.sh /usr/bin/wait-for-databases

COPY --chmod=755 src/celery.sh /usr/bin/celery-commands

COPY --chmod=755 src/celery-cmd /usr/bin/celery-cmd

RUN python -m pip install -U pip setuptools wheel && \
    pip install --src /usr/src -r requirements.txt

# 755 em tudo: sem isso a cópia traz as permissões do host (700 no macOS), e um UID que não é
# o dono (ex.: UID aleatório do OpenShift, grupo 0) não consegue ler manage.py nem o pacote
COPY --chmod=755 src/ /usr/src/project

RUN yes w | pip install -e .

RUN mkdir -p /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode && \
    chmod g=u /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode
EXPOSE 8000
