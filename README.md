# OpenGeoSGB

Instância [GeoNode](https://geonode.org/) 5 do Serviço Geológico do Brasil (SGB/CPRM).

Este repositório é um projeto Django gerado a partir do template [`geonode-project`](https://github.com/GeoNode/geonode-project). Ele estende o GeoNode com settings, templates, URLs e fixtures próprios (app `opengeosgb`, em `src/`) e traz a configuração Docker do stack completo.

## Repositórios relacionados

| Repositório | Papel |
|---|---|
| [`nds-cprm/geonode`](https://github.com/nds-cprm/geonode) (branch `iso19115-3_2018-support`) | Fork do núcleo do GeoNode, instalado via `src/requirements.txt`. Mudanças em modelos, catálogo/CSW, upload e templates XML de metadados vão para lá. |
| [`nds-cprm/geonode-docker`](https://github.com/nds-cprm/geonode-docker) (branch `opengeosgb`) | Submódulo `docker/`, com os Dockerfiles do nginx, GeoServer, geoserver_data, PostGIS e letsencrypt. |
| [`GeoNode/geonode-mapstore-client`](https://github.com/GeoNode/geonode-mapstore-client) | Frontend (React/MapStore). Os templates sobrescritos ficam em `src/opengeosgb/templates/geonode-mapstore-client/`. |
| [`GeoNode/geonode-project`](https://github.com/GeoNode/geonode-project) | Template de origem, útil para comparar com a versão upstream. |

## Stack

| Serviço | Imagem | Função |
|---|---|---|
| `django` | construída de `Dockerfile` | GeoNode (uWSGI, porta 8000) |
| `celery` | mesma imagem do `django` | Workers de tarefas assíncronas e harvesting |
| `geonode` | construída de `docker/docker/nginx` | nginx (portas 8080/8443 no container) |
| `geoserver` | construída de `docker/docker/geoserver` | GeoServer 2.27 sobre Tomcat 9 |
| `data-dir-conf` | construída de `docker/docker/geoserver_data` | Popula o data dir do GeoServer |
| `db` | construída de `docker/docker/postgis` | PostgreSQL + PostGIS |
| `letsencrypt` | construída de `docker/docker/letsencrypt` | Certificados (desativado: `replicas: 0`) |
| `memcached`, `redis` | oficiais | Cache e broker do celery |
| `mailserver` | `python:3.11-alpine` | SMTP de depuração (porta 1025), só para desenvolvimento |

O compose base (`docker-compose.yml`) é sempre combinado com o override `docker-compose.opengeosgb.yml`. Toda customização do stack vai no override; o arquivo base fica igual ao do template.

## Primeiros passos

Requisitos: Docker com Compose v2, ou Podman 5+ com `podman compose` (que usa o `docker-compose` ou o `podman-compose` instalado).

```bash
git clone --recurse-submodules https://github.com/nds-cprm/opengeosgb.git
cd opengeosgb
# se já tiver clonado sem os submódulos:
git submodule update --init
```

### Arquivo `.env`

Os serviços leem as variáveis de `.env`. Use `.env.sample` como referência ou gere um novo arquivo:

```bash
python create-envfile.py --env_type dev --hostname localhost
```

| Opção | Descrição |
|---|---|
| `--env_type` | `dev` (DEBUG ligado, sem SSL), `test` (certificado de teste) ou `prod` (padrão; certificado via Let's Encrypt) |
| `--hostname` | Endereço que serve o GeoNode (padrão `localhost`) |
| `--https` | Ativa SSL |
| `--email` | E-mail do administrador; obrigatório com `--https` |
| `--geonodepwd`, `--geoserverpwd`, `--pgpwd`, `--dbpwd`, `--geodbpwd`, `--clientid`, `--clientsecret`, `--secret_key` | Senhas e segredos; os omitidos recebem valores aleatórios |
| `--noinput` | Não pede confirmação para sobrescrever o `.env` |

### Subir o stack

O script `opengeosgb-alias.sh` define o comando `geonode-docker`, que combina os dois arquivos compose e detecta se a máquina usa Docker ou Podman:

```bash
source opengeosgb-alias.sh             # bash ou zsh
geonode-docker build
geonode-docker up -d
geonode-docker logs -f django celery
```

Para forçar uma engine: `CONTAINER_ENGINE=podman geonode-docker up -d` (ou `docker`).

Na primeira execução, o django aplica as migrações, carrega os fixtures e roda o `collectstatic`, o que pode levar vários minutos. Nesse intervalo o healthcheck pode marcar o container como `unhealthy` e o `up` aborta antes de iniciar `celery` e `geoserver`. Espere o django responder e rode `geonode-docker up -d` de novo.

Comandos úteis:

```bash
geonode-docker exec django python manage.py <comando>
geonode-docker exec django python manage.py clear_default_supplemental_information --dry-run
geonode-docker down          # para e remove os containers (os volumes ficam)
```

## Arquitetura das imagens (linux/amd64)

Todas as imagens construídas pelo stack são `linux/amd64`, inclusive em Macs Apple Silicon (onde rodam emuladas). `memcached`, `redis` e `mailserver` não são construídos e rodam na arquitetura nativa.

A arquitetura é escolhida em dois pontos:

- Cada Dockerfile usa `FROM --platform=$TARGETPLATFORM ...`, para baixar a imagem base na arquitetura pedida, e não na do host.
- O `docker-compose.opengeosgb.yml` passa `TARGETPLATFORM=linux/amd64` em `build.args` de cada serviço com `build`. O `platform: linux/amd64` do serviço também está definido, mas não afeta a build.

Isso é necessário porque o `podman compose` delega ao `docker-compose` e, nesse caminho, `platform` e `build.platforms` são ignorados na build. Sem o `FROM --platform`, o Podman reaproveita uma base arm64 que esteja em cache, ou tenta baixá-la, e a imagem final sai arm64. Num build do postgis sem cache o resultado é `no image found in image index for architecture "arm64"`, porque essa base só existe em amd64. Com o `FROM --platform`, não é preciso baixar as bases à mão.

Os Dockerfiles não declaram `ARG TARGETPLATFORM`: o buildah recusa redeclarar esse nome (`attempted to redefine "TARGETPLATFORM"`), mesmo com valor padrão. Por isso o valor vem do overlay, e um `podman build` direto, sem o `--build-arg TARGETPLATFORM=...`, usa a arquitetura do host.

Para conferir o resultado: `podman image inspect <imagem> --format '{{.Architecture}}'`.

Para gerar também arm64 no futuro, remova a linha `TARGETPLATFORM` dos `args` do overlay e construa com `--platform linux/amd64,linux/arm64`, porque o buildx preenche o `TARGETPLATFORM` de cada variante. O postgis deve continuar em amd64, porque a base `postgis/postgis:15-3.5-alpine` não tem arm64.

## Execução sem root

`django`, `celery` e `geoserver` rodam com `user: '1000:0'`: UID arbitrário e grupo 0. As imagens dão aos diretórios graváveis a permissão `g=u`, então qualquer UID do grupo 0 consegue gravar neles. Isso também deixa o stack compatível com plataformas que atribuem UIDs aleatórios, como o OpenShift.

Pontos de atenção:
- Scripts copiados para as imagens precisam de permissão de leitura, não só de execução. O `Dockerfile` usa `COPY --chmod=755`, inclusive no `COPY src/`, que exige BuildKit no Docker (padrão nas versões atuais) ou buildah no Podman. Sem isso, a cópia traz as permissões do host (700 num clone feito no macOS) e `manage.py`, o pacote `opengeosgb` e os fixtures ficam `root:root 700`: um UID que não seja o dono, como o aleatório do OpenShift, recebe `Permission denied`. O bind mount de `./src` em desenvolvimento esconde o problema.
- O GeoServer recebe `HOME=/tmp`: no Podman, o `HOME` de um UID sem entrada no `/etc/passwd` seria o `WORKDIR` (`/usr/local/tomcat/tmp`), que não é gravável.
- Volumes criados quando os containers rodavam como root podem ter arquivos que o UID 1000 não consegue gravar. Se aparecer `Permission denied`, ajuste o grupo e as permissões dentro do volume (`chgrp -R 0` e `chmod -R g=u`).

## Podman no macOS

Ajustes necessários além dos já descritos:
- O Podman sem root não publica a porta 80. Libere com `podman machine ssh "sudo sysctl -w net.ipv4.ip_unprivileged_port_start=80"` (vale até a máquina reiniciar).
- O nginx usa `RESOLVER=127.0.0.11`, que só existe no Docker; no Podman, as requisições ficam pendentes e dão timeout. Defina `RESOLVER` no `.env` com o DNS da rede do Podman: o `nameserver` do `/etc/resolv.conf` de um container do stack (por exemplo, `RESOLVER=10.89.0.1`).
- Se os `apk add` dos builds baseados em Alpine falharem com `DNS: transient error`, o DNS da máquina do Podman travou. Reinicie-a com `podman machine stop && podman machine start` e repita o `sysctl` da porta 80.
- `docker/docker/postgis/initdb-geonode.sh` precisa estar com permissão `755` no host. Com `0700`, o usuário `postgres` não consegue executá-lo, os usuários do GeoNode não são criados e o django falha com `password authentication failed`.

## Customizações do projeto

- **Settings:** toda customização vai em `src/opengeosgb/local_settings.py`, que importa `geonode.settings`. `settings.py` só contém o que é estrutural do template.
- **Templates e estáticos:** arquivos em `src/opengeosgb/templates/` e `src/opengeosgb/static/` sobrescrevem os do GeoNode e do mapstore-client quando têm o mesmo caminho relativo.
- **Metadados:** `CATALOGUE_DEFAULT_FORMAT=ISO19115-3_2018` troca o perfil de metadados de ISO 19139 para ISO 19115-3 (lógica no fork do GeoNode).
- **Escala:** os recursos ganham o campo "Escala" no painel de informações e um filtro "Escala" no catálogo (`src/opengeosgb/metadata/`).
- **Autenticação:** login com Google, ORCID e gov.br (OpenID Connect), formulários próprios e reCAPTCHA opcional (`RECAPTCHA_ENABLED`).
- **Páginas institucionais:** flatpages em `/pages/`, editadas no admin com um editor TinyMCE restrito; o HTML é sanitizado ao salvar e ao exibir. Cada idioma é uma página separada (`/pages/sobre/` e `/pages/about/`).
- **LGPD:** faixa de consentimento de cookies; o Google Tag Manager (`GOOGLE_TAG_MANAGER_ID`) só é carregado depois do aceite. Os endereços da política de cookies e da página "Sobre" são configuráveis (`COOKIE_POLICY_URL`, `COOKIE_POLICY_URL_EN`).
- **Links legados:** `datasets/<alternate>/metadata_detail`, do GeoNode 4, redireciona para `metadata/<pk>`.

## Backup e restore

Os scripts ficam em `src/opengeosgb/br/`.

```bash
geonode-docker exec django sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./opengeosgb/br/backup.sh $BKP_FOLDER_NAME'
geonode-docker exec django sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./opengeosgb/br/restore.sh $BKP_FOLDER_NAME'
```

- `BKP_FOLDER_NAME`: pasta compartilhada de backup, a partir da raiz (padrão `backup_restore`).
- `SOURCE_URL`: URL do servidor que gerou o backup.
- `TARGET_URL`: URL do servidor que vai ser sincronizado.

## Desenvolvimento

- O override monta `./src` em `/usr/src/project`, então alterações no código aparecem nos containers sem rebuild. O uWSGI recarrega o código quando `src/opengeosgb/wsgi.py` é modificado (`touch src/opengeosgb/wsgi.py`).
- Há uma configuração de Dev Container em `.devcontainer/` (serviço `django`, workspace `/usr/src/project`).
- Lint: `flake8`, com a configuração de `.flake8` (linhas de até 200 caracteres).
- O projeto não tem suíte de testes própria; os testes do núcleo ficam no fork do GeoNode.

## Estrutura

```
.
├── Dockerfile                      # imagem do django/celery
├── docker-compose.yml              # compose base (template geonode-project)
├── docker-compose.opengeosgb.yml   # override do projeto
├── opengeosgb-alias.sh             # comando geonode-docker (Docker ou Podman)
├── create-envfile.py               # gerador de .env
├── docker/                         # submódulo nds-cprm/geonode-docker
└── src/
    ├── entrypoint.sh, tasks.py     # inicialização do container (invoke)
    ├── celery-cmd                  # inicialização do celery
    ├── requirements.txt            # aponta para o fork do GeoNode
    ├── fixtures/
    └── opengeosgb/                 # app Django do projeto
```
