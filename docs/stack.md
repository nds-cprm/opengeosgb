# Repositórios e stack

## Repositórios relacionados

| Repositório | Papel |
|---|---|
| [`GeoNode/geonode`](https://github.com/GeoNode/geonode) (tag `5.0.3`) | Núcleo do GeoNode, sem fork, instalado via `src/requirements.txt`. Personalizações são feitas por override no app `opengeosgb`. |
| [`nds-cprm/geonode-docker`](https://github.com/nds-cprm/geonode-docker) (branch `unifica-opengeosgb`, que vai substituir o `opengeosgb`) | Submódulo `docker/`, com os Dockerfiles do nginx, GeoServer, PostGIS e letsencrypt. É compartilhado com o geosdc (Defesa Civil de SC). |
| [`GeoNode/geonode-mapstore-client`](https://github.com/GeoNode/geonode-mapstore-client) | Frontend (React/MapStore). Os templates sobrescritos ficam em `src/opengeosgb/templates/geonode-mapstore-client/`. |
| [`GeoNode/geonode-project`](https://github.com/GeoNode/geonode-project) | Template de origem, útil para comparar com a versão upstream. |

## Stack

| Serviço | Imagem | Função |
|---|---|---|
| `django` | `ghcr.io/nds-cprm/opengeosgb-geonode`, publicada pelo GitHub Actions ou construída localmente do `Dockerfile` (tag `local`) | GeoNode (uWSGI, porta 8000) |
| `celery` | mesma imagem do `django` | Workers de tarefas assíncronas e harvesting |
| `geonode` | construída de `docker/docker/nginx` | nginx (portas 8080/8443 no container) |
| `geoserver` | construída de `docker/docker/geoserver` | GeoServer 2.28 sobre Tomcat 9 (Java 17), com as extensões `excel` e `geopkg-output` e as fontes do SGB. No primeiro boot, com o volume sem `global.xml`, a própria imagem extrai o data dir do GeoNode (não há mais o `data-dir-conf`) |
| `db` | construída de `docker/docker/postgis` | PostgreSQL + PostGIS |
| `letsencrypt` | construída de `docker/docker/letsencrypt` | Certificados (desativado: `replicas: 0`) |
| `memcached`, `redis` | oficiais | Cache e broker do celery |
| `mailserver` | `python:3.11-alpine` | SMTP de depuração (porta 1025), só para desenvolvimento |

O compose base (`docker-compose.yml`) é sempre combinado com o override `docker-compose.opengeosgb.yml`. Toda customização do stack vai no override; o arquivo base fica igual ao do template.
