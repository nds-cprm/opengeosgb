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
# Todas as chaves são declaradas aqui para não herdar os valores da imagem base (que descrevem a base,
# não o projeto). VERSION, REVISION e CREATED vêm do build, por exemplo:
#   --build-arg VERSION=$(git describe --tags --always) --build-arg REVISION=$(git rev-parse HEAD) \
#   --build-arg CREATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ARG GEONODE_BASE_IMAGE
ARG VERSION=dev
ARG REVISION=unknown
ARG CREATED=unknown
LABEL org.opencontainers.image.title="OpenGeoSGB" \
      org.opencontainers.image.description="Instância GeoNode do Serviço Geológico do Brasil (SGB/CPRM)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.authors="NDS CPRM" \
      org.opencontainers.image.vendor="Serviço Geológico do Brasil (SGB/CPRM)" \
      org.opencontainers.image.url="https://github.com/nds-cprm/opengeosgb" \
      org.opencontainers.image.source="https://github.com/nds-cprm/opengeosgb" \
      org.opencontainers.image.documentation="https://github.com/nds-cprm/opengeosgb#readme" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.base.name="${GEONODE_BASE_IMAGE}"

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

# Correções de segurança: versões mais novas que as fixadas pelo GeoNode (ex.: Pillow). --no-deps porque o
# resolvedor do pip recusaria a combinação; o build-smoke-test.sh aceita só essas divergências no pip check.
COPY src/requirements-overrides.txt .
RUN pip install --no-deps -r requirements-overrides.txt

# 755 (e não só +x): scripts precisam de leitura para rodar com um usuário que não é root
COPY --chmod=755 src/wait-for-databases.sh /usr/bin/wait-for-databases
COPY --chmod=755 src/celery.sh /usr/bin/celery-commands
COPY --chmod=755 src/celery-cmd /usr/bin/celery-cmd

# 755 em tudo: sem isso a cópia traz as permissões do host (700 no macOS), e um UID que não é
# o dono (ex.: UID aleatório do OpenShift, grupo 0) não consegue ler manage.py nem o pacote
COPY --chmod=755 src/ .

# O smoke test da base confere o venv depois dos pacotes do projeto (GDAL, psycopg2, invoke, pip check...).
# O build-smoke-test.sh o roda aceitando só as divergências do pip check de requirements-overrides.txt
RUN yes w | pip install -e . && \
    ./build-smoke-test.sh

EXPOSE 8000
