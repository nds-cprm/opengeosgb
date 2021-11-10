#!/bin/bash

# Exit script in case of error
set -e

# pip install -e git+https://alvaro.barcellos:nds%40cprm@gitlab.ti.lemaf.ufla.br/zetta/ide-zetta-client.git@teste_cprm#egg=django_geonode_mapstore_client
# pip install -e git+https://github.com/nds-cprm/geonode-mapstore-client.git@3.2.x#egg=django_geonode_mapstore_client

# Start cron services
# service memcached restart
service cron restart

echo $"\n\n\n"
echo "-----------------------------------------------------"
echo "STARTING DJANGO ENTRYPOINT $(date)"
echo "-----------------------------------------------------"

invoke update > $GEONODE_ROOT/invoke.log 2>&1

source $HOME/.bashrc
source $HOME/.override_env

echo DOCKER_API_VERSION=$DOCKER_API_VERSION
echo POSTGRES_USER=$POSTGRES_USER
echo POSTGRES_PASSWORD=$POSTGRES_PASSWORD
echo DATABASE_URL=$DATABASE_URL
echo GEODATABASE_URL=$GEODATABASE_URL
echo SITEURL=$SITEURL
echo ALLOWED_HOSTS=$ALLOWED_HOSTS
echo GEOSERVER_PUBLIC_LOCATION=$GEOSERVER_PUBLIC_LOCATION
echo MONITORING_ENABLED=$MONITORING_ENABLED
echo MONITORING_HOST_NAME=$MONITORING_HOST_NAME
echo MONITORING_SERVICE_NAME=$MONITORING_SERVICE_NAME
echo MONITORING_DATA_TTL=$MONITORING_DATA_TTL

invoke waitfordbs > $GEONODE_ROOT/invoke.log 2>&1
echo "waitfordbs task done"

cmd="$@"

echo DOCKER_ENV=$DOCKER_ENV

if [ -z ${DOCKER_ENV} ] || [ ${DOCKER_ENV} = "development" ]
then
    echo "Executing standard Django server $cmd for Development"
else
    if [ ${IS_CELERY} = "true" ]  || [ ${IS_CELERY} = "True" ]
    then
        cmd=$CELERY_CMD
        echo "Executing Celery server $cmd for Production"
    else

        echo "running migrations"
        invoke migrations > $GEONODE_ROOT/invoke.log 2>&1
        echo "migrations task done"

        invoke prepare > $GEONODE_ROOT/invoke.log 2>&1
        echo "prepare task done"

        if [ ${FORCE_REINIT} = "true" ]  || [ ${FORCE_REINIT} = "True" ] || [ ! "/mnt/volumes/statics/geonode_init.lock" ]; then
            invoke updategeoip > $GEONODE_ROOT/invoke.log 2>&1
            echo "updategeoip task done"
            invoke fixtures > $GEONODE_ROOT/invoke.log 2>&1
            echo "fixture task done"
            invoke monitoringfixture > $GEONODE_ROOT/invoke.log 2>&1
            echo "monitoringfixture task done"
            invoke initialized > $GEONODE_ROOT/invoke.log 2>&1
            echo "initialized"
        fi

        echo "refresh static data"
        invoke statics > $GEONODE_ROOT/invoke.log 2>&1
        echo "static data refreshed"
        invoke waitforgeoserver > $GEONODE_ROOT/invoke.log 2>&1
        echo "waitforgeoserver task done"
        invoke geoserverfixture > $GEONODE_ROOT/invoke.log 2>&1
        echo "geoserverfixture task done"
        invoke updateadmin > $GEONODE_ROOT/invoke.log 2>&1
        echo "updateadmin task done"

        cmd=$UWSGI_CMD
        echo "Executing UWSGI server $cmd for Production"
    fi
fi

echo "-----------------------------------------------------"
echo "FINISHED DJANGO ENTRYPOINT --------------------------"
echo "-----------------------------------------------------"

# Run the CMD
echo "got command $cmd"
exec $cmd
