FROM geonode/geonode-base:latest-ubuntu-22.04

# https://specs.opencontainers.org/image-spec/annotations/
LABEL org.opencontainers.image.title="GeoNode" \
    org.opencontainers.image.version="4.4.4" \
    org.opencontainers.image.authors="GeoNode development team & NDS CPRM"    

RUN mkdir -p /usr/src/opengeosgb

RUN apt-get update -y && apt-get install curl wget unzip gnupg2 locales -y

RUN sed -i -e 's/# C.UTF-8 UTF-8/C.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# add bower and grunt command
COPY src /usr/src/opengeosgb/
WORKDIR /usr/src/opengeosgb

#COPY src/monitoring-cron /etc/cron.d/monitoring-cron
#RUN chmod 0644 /etc/cron.d/monitoring-cron
#RUN crontab /etc/cron.d/monitoring-cron
#RUN touch /var/log/cron.log
#RUN service cron start

COPY src/wait-for-databases.sh /usr/bin/wait-for-databases
RUN chmod +x /usr/bin/wait-for-databases
RUN chmod +x /usr/src/opengeosgb/tasks.py \
    && chmod +x /usr/src/opengeosgb/entrypoint.sh

COPY src/celery.sh /usr/bin/celery-commands
RUN chmod +x /usr/bin/celery-commands

COPY src/celery-cmd /usr/bin/celery-cmd
RUN chmod +x /usr/bin/celery-cmd

# Install "geonode-contribs" apps
# RUN cd /usr/src; git clone https://github.com/GeoNode/geonode-contribs.git -b master
# Install logstash and centralized dashboard dependencies
# RUN cd /usr/src/geonode-contribs/geonode-logstash; pip install --upgrade  -e . \
#     cd /usr/src/geonode-contribs/ldap; pip install --upgrade  -e .

RUN yes w | pip install --src /usr/src -r requirements.txt -c constraints.txt && \
    yes w | pip install -c constraints.txt -e .

# Cleanup apt update lists
RUN apt-get autoremove --purge &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode && \
    chmod g+u /mnt/volumes/statics /geoserver_data/data /backup_restore /data /var/log/geonode

# Export ports
EXPOSE 8000

# We provide no command or entrypoint as this image can be used to serve the django project or run celery tasks
# ENTRYPOINT /usr/src/opengeosgb/entrypoint.sh
