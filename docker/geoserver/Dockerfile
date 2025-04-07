ARG BASE_IMAGE_VERSION
FROM geonode/geoserver:${BASE_IMAGE_VERSION}

COPY fonts/ /usr/share/fonts/opengeosgb

RUN set -xe && \
    sed -i 's/^source \/root\/.bashrc/export TMPDIR=\/tmp/' entrypoint.sh set_geoserver_auth.sh && \    
    sed -i 's/\/root\/.override_env/\/tmp\/.override_env/' entrypoint.sh set_geoserver_auth.sh && \
    # o de baixo tinha que ir pro dockerfile do geoserver
    # chmod -R g=u /usr/local/tomcat/conf/catalina.properties $CATALINA_HOME/webapps/geoserver/WEB-INF/web.xml
    chmod g=u /usr/local/tomcat/conf $CATALINA_HOME/webapps/geoserver/WEB-INF
