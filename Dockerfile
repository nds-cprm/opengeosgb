# Base do GeoNode 5.0.x em multi-stage (Ubuntu 24.04, GDAL 3.8.4 do apt, sem compiladores), construída
# de docker/base/ubuntu/multi-stage/Dockerfile do nds-cprm/geonode (branch geonode-base-multistage). Traz
# compilados os pacotes do GeoNode 5.0.x sem wheel para Python 3.12 (GDAL, psycopg2, pylibmc, uWSGI).
# Há uma variante da base por versão major do PostgreSQL (ubuntu-24.04-pg15, ubuntu-24.04-pg17), escolhida
# pelo build arg POSTGRES_CLIENT_VERSION, que o compose preenche com o POSTGRES_BASE_IMAGE_VERSION do .env
# (a mesma versão da imagem postgis).
# Acrescentar -devel ao GEONODE_BASE_IMAGE usa a variante com compiladores e pacotes -dev (para depurar
# ou instalar pacotes sem wheel), por exemplo docker.io/ndscprm/geonode-base:ubuntu-24.04-pg17-devel
ARG POSTGRES_CLIENT_VERSION=17
ARG GEONODE_BASE_IMAGE=docker.io/ndscprm/geonode-base:ubuntu-24.04-pg${POSTGRES_CLIENT_VERSION}
FROM ${GEONODE_BASE_IMAGE}

# https://specs.opencontainers.org/image-spec/annotations/
LABEL org.opencontainers.image.title="OpenGeoSGB/GeoNode" \
    org.opencontainers.image.version="dev" \
    org.opencontainers.image.authors="GeoNode development team & NDS CPRM"    

# A base já traz curl, wget, unzip e gnupg2, e o venv com pip/setuptools/wheel atualizados e o invoke.
# Ela não define locale; o C.UTF-8 já vem na glibc do Ubuntu 24.04, sem "locales"/"locale-gen".
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

WORKDIR /usr/src/project

# Dependências antes do código, em camada própria: mudar src/ não reinstala o GeoNode.
# A base não tem compilador: pacotes novos no requirements.txt precisam ter wheel (ou ser Python puro).
# Os diretórios dos volumes ganham g=u para um UID arbitrário do grupo 0 (rootless, OpenShift).
COPY src/requirements.txt .
RUN pip install --src /usr/src -r requirements.txt && \
    mkdir -p /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode && \
    chmod g=u /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode

# 755 (e não só +x): scripts precisam de leitura para rodar com um usuário que não é root
COPY --chmod=755 src/wait-for-databases.sh /usr/bin/wait-for-databases
COPY --chmod=755 src/celery.sh /usr/bin/celery-commands
COPY --chmod=755 src/celery-cmd /usr/bin/celery-cmd

# 755 em tudo: sem isso a cópia traz as permissões do host (700 no macOS), e um UID que não é
# o dono (ex.: UID aleatório do OpenShift, grupo 0) não consegue ler manage.py nem o pacote
COPY --chmod=755 src/ .

# O smoke test da base confere o venv depois dos pacotes do projeto (GDAL, psycopg2, invoke, pip check...)
RUN yes w | pip install -e . && \
    geonode-base-smoke-test

EXPOSE 8000
