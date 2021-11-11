ARG DEBIAN_VERSION=bullseye
ARG PYTHON_VERSION=3.8
ARG BASE_IMAGE=python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}

FROM $BASE_IMAGE AS BUILD
LABEL mantainer="NDS CPRM"

ENV GEONODE_ROOT=/usr/src/opengeosgb \
    GEONODE_VENV=/opt/venv
    #GEONODE_CONTRIBS=/usr/src/geonode-contribs

## Prepraing dependencies
# GDAL 3 & PROJ4 -> Build from source (GDAL > 3.2.x & PROJ > 6)
# GDAL -> https://github.com/OSGeo/gdal
# PROJ -> https://github.com/OSGeo/PROJ
#RUN apt-get update && apt-get install -y devscripts build-essential debhelper pkg-kde-tools sharutils
## RUN git clone https://salsa.debian.org/debian-gis-team/proj.git /tmp/proj
## RUN cd /tmp/proj && debuild -i -us -uc -b && dpkg -i ../*.deb

# To get GDAL 3.2.1 to fix this issue https://github.com/OSGeo/gdal/issues/1692
# TODO: The following line should be removed if base image upgraded to Bullseye
# RUN echo "deb http://deb.debian.org/debian/ bullseye main contrib non-free" | tee /etc/apt/sources.list.d/debian.list

# This section is borrowed from the official Django image but adds GDAL and others
RUN set -xe && \
    apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
      git build-essential libgdal-dev libpq-dev libxml2-dev \
      libxslt1-dev zlib1g-dev libjpeg-dev libmemcached-dev  \
      libldap2-dev libsasl2-dev libffi-dev && \
    apt-get -y autoremove --purge && \
    rm -rf /var/lib/apt/lists/*

# add bower and grunt command
COPY . $GEONODE_ROOT
WORKDIR $GEONODE_ROOT

# Install virtual env
RUN set -xe && \
    python -m venv $GEONODE_VENV

# Add venv to PATH
ENV PATH=$GEONODE_VENV/bin:$PATH

# Install dependencies
RUN set -xe && \
    pip install --upgrade --no-cache-dir -r requirements.txt &&  \
    pip install --no-cache-dir pygdal==$(gdal-config --version).* &&  \
    pip install --no-cache-dir flower==0.9.4 && \
    pip install --no-cache-dir pylibmc sherlock && \
    # Django Haystack only supports these versions
    pip install --no-cache-dir "elasticsearch>=2.0.0,<3.0.0"

# Install Main Geonode Module
RUN set -xe && \
    pip install --no-cache-dir --upgrade  -e .

# Install Geonode contribs
RUN set -xe && \
    pip install --no-cache-dir -e "git+https://github.com/GeoNode/geonode-contribs.git@master#egg=geonode_logstash&subdirectory=geonode-logstash" && \
    pip install --no-cache-dir -e "git+https://github.com/GeoNode/geonode-contribs.git@master#egg=geonode_ldap&subdirectory=ldap"

# Cleaned Image
FROM $BASE_IMAGE AS RELEASE

ARG DEBIAN_VERSION

ENV GEONODE_ROOT=/usr/src/opengeosgb \
    GEONODE_VENV=/opt/venv

COPY --from=BUILD $GEONODE_VENV $GEONODE_VENV
COPY --from=BUILD $GEONODE_ROOT $GEONODE_ROOT

# Add venv to PATH
ENV PATH=$GEONODE_VENV/bin:$PATH

WORKDIR $GEONODE_ROOT

# PostgreSQL Repos
RUN set -xe && \
    apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        gnupg wget && \
    echo "deb http://apt.postgresql.org/pub/repos/apt/ ${DEBIAN_VERSION}-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list && \
    # echo "deb http://deb.debian.org/debian/ stable main contrib non-free" | tee /etc/apt/sources.list.d/debian.list
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get -y purge wget gnupg && \
    apt-get -y autoremove --purge && \
    rm -rf /var/lib/apt/lists/*

# Dependency binaries
RUN set -xe && \
    apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        zip unzip gettext geoip-bin cron gdal-bin postgresql-client-13 && \
    apt-get -y autoremove --purge && \
    rm -rf /var/lib/apt/lists/*

# Executables
#COPY monitoring-cron /etc/cron.d/monitoring-cron
RUN set -xe && \
    mv monitoring-cron /etc/cron.d/monitoring-cron && \
    chmod 0644 /etc/cron.d/monitoring-cron && \
    crontab /etc/cron.d/monitoring-cron && \
    touch /var/log/cron.log && \
    service cron start

#COPY wait-for-databases.sh /usr/bin/wait-for-databases
RUN set -xe && \
    mv wait-for-databases.sh /usr/bin/wait-for-databases && \
    chmod +x /usr/bin/wait-for-databases && \
    chmod +x tasks.py &&  \
    chmod +x entrypoint.sh

#COPY celery.sh /usr/bin/celery-commands
RUN set -xe && \
    mv celery.sh /usr/bin/celery-commands && \
    chmod +x /usr/bin/celery-commands

#COPY celery-cmd /usr/bin/celery-cmd
RUN set -xe && \
    mv celery-cmd /usr/bin/celery-cmd && \
    chmod +x /usr/bin/celery-cmd

ENTRYPOINT /usr/src/opengeosgb/entrypoint.sh
