# OpenGeoSGB

Instância [GeoNode](https://geonode.org/) 5 do Serviço Geológico do Brasil (SGB/CPRM).

Este repositório é um projeto Django gerado a partir do template [`geonode-project`](https://github.com/GeoNode/geonode-project). Ele estende o GeoNode com settings, templates, URLs e fixtures próprios (app `opengeosgb`, em `src/`) e traz a configuração Docker do stack completo.

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
| `django` | construída de `Dockerfile` | GeoNode (uWSGI, porta 8000) |
| `celery` | mesma imagem do `django` | Workers de tarefas assíncronas e harvesting |
| `geonode` | construída de `docker/docker/nginx` | nginx (portas 8080/8443 no container) |
| `geoserver` | construída de `docker/docker/geoserver` | GeoServer 2.28 sobre Tomcat 9 (Java 17), com as extensões `excel` e `geopkg-output` e as fontes do SGB. No primeiro boot, com o volume sem `global.xml`, a própria imagem extrai o data dir do GeoNode (não há mais o `data-dir-conf`) |
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

## Versões e imagens publicadas

A imagem do Django é construída pelo workflow [`.github/workflows/docker-image.yml`](.github/workflows/docker-image.yml) e publicada no GitHub Container Registry como `ghcr.io/nds-cprm/opengeosgb-geonode`, para `linux/amd64` e `linux/arm64` (cada uma num runner nativo), sobre a base `ubuntu-24.04-pg17`. As imagens do submódulo `docker/` (nginx, GeoServer, PostGIS, letsencrypt) não fazem parte dele.

| Evento | Tags publicadas |
|---|---|
| tag git `vX.Y.Z` | `X.Y.Z`, e `latest` se for a maior versão estável entre as tags `vX.Y.Z` do repositório |
| tag git `vX.Y.Z-rc.N` | `X.Y.Z-rc.N` (pré-release, nunca `latest`) |
| push no `main` | `devel` |
| pull request para o `main` | nenhuma: só constrói, com o smoke test |
| manual (*Run workflow*) | só constrói; com *Publicar no GHCR* marcado, publica com as tags da ref escolhida |

**Política de versões.** As versões do opengeosgb seguem o [SemVer](https://semver.org/lang/pt-BR/) e não acompanham as do GeoNode. A `v1.0.0` é a primeira, sobre o GeoNode 5.0.3.
- **MAJOR:** mudança que exige ação ao atualizar um ambiente: versão minor ou major nova do GeoNode (5.0 → 5.1), variável do `.env` removida ou renomeada, migração manual de dados, nova versão major do PostgreSQL.
- **MINOR:** funcionalidade nova compatível, inclusive uma versão patch nova do GeoNode (5.0.3 → 5.0.4).
- **PATCH:** correções, traduções e atualizações de segurança de dependências (por exemplo, o `requirements-overrides.txt`).

Uma tag publicada não é reconstruída: atualizações da imagem base ou de dependências saem numa versão patch nova. A versão do GeoNode de cada imagem fica no label `io.github.nds-cprm.opengeosgb.geonode.version` e deve constar nas notas da release:

```bash
docker image inspect ghcr.io/nds-cprm/opengeosgb-geonode:1.0.0 \
  --format '{{ index .Config.Labels "io.github.nds-cprm.opengeosgb.geonode.version" }}'
```

**Uso no compose.** O `docker-compose.opengeosgb.yml` dá à imagem do django e do celery o nome `ghcr.io/nds-cprm/opengeosgb-geonode:${OPENGEOSGB_VERSION}` (padrão `local`):
- em desenvolvimento, `OPENGEOSGB_VERSION=local` é a imagem construída por `geonode-docker build`;
- nos ambientes, use uma versão publicada (`OPENGEOSGB_VERSION=1.0.0`, ou `devel` para o `main`) e baixe-a com `geonode-docker pull django celery`. Não construa o django nesses ambientes: o build local sobrescreveria a tag publicada. Para construir só o resto, use `geonode-docker build geonode geoserver db`.

O override monta `./src` sobre o código da imagem. Num ambiente que usa uma versão publicada, deixe o checkout na mesma tag (`git checkout v1.0.0`) para que o código montado seja o da imagem.

### Lint (Python e Docker)

O workflow [`.github/workflows/lint.yml`](.github/workflows/lint.yml) roda em pushes no `main` e em pull requests. Ele tem quatro jobs, e qualquer aviso faz o job falhar. Os avisos do flake8 e do shellcheck viram anotações nas linhas do PR.

| Job | O que verifica | Configuração |
|---|---|---|
| Python | `flake8 src` | `.flake8` |
| Dockerfile | `hadolint` no `Dockerfile` | `.hadolint.yaml` |
| Scripts | `shellcheck` nos scripts versionados, achados pela extensão `.sh` ou pelo shebang (fora o submódulo `docker/`) | `SHELLCHECK_SEVERITY` no workflow |
| Compose | `docker compose config` do compose base com o override, sobre o `.env.sample` | — |

O shellcheck só falha a partir de `warning`. Os `note`, quase todos SC2086 (variável sem aspas), ficam de fora: são dezenas nos scripts herdados do template, e pôr aspas pode mudar o comportamento. O `celery-cmd`, por exemplo, conta com variáveis vazias sumindo da linha de comando. Corrija-os aos poucos e depois suba a severidade para `info`.

As versões das ferramentas ficam fixas no `env` do workflow. Para rodar localmente:

```bash
flake8 src
docker run --rm -i -v "$PWD/.hadolint.yaml:/.config/hadolint.yaml:ro" \
  docker.io/hadolint/hadolint:v2.15.1 hadolint - < Dockerfile
docker run --rm -v "$PWD:/mnt:ro" -w /mnt docker.io/koalaman/shellcheck:v0.11.0 --severity=warning \
  opengeosgb-alias.sh opengeosgb-tests src/*.sh src/celery-cmd src/opengeosgb/br/*.sh
```

Para ignorar uma regra num ponto só, use `# hadolint ignore=DLxxxx` ou `# shellcheck disable=SCxxxx` logo acima da linha, com o motivo.

### Dependabot

O [`.github/dependabot.yml`](.github/dependabot.yml) abre PRs semanais, às segundas, para dois ecossistemas. Cada PR passa pelo build, pelo smoke test, pelo Trivy e pelo lint.
- **GitHub Actions:** atualizações minor e patch num único PR, e as major em separado. O `trivy-action` é atualizado pelo SHA; antes do merge, confira os advisories e atualize junto o `SCAN_TRIVY_VERSION`.
- **pip (`src/`):** na prática, as versões forçadas do `requirements-overrides.txt`.

Estes ficam de fora e precisam ser atualizados à mão:
- a imagem base do `Dockerfile`, cujo `FROM` é montado por `ARG`;
- as tags git do `src/requirements.txt` (GeoNode e os apps da nds-cprm), porque o Dependabot não atualiza referências git de pip;
- as versões das imagens no `.env`.

O submódulo `docker/` também fica de fora: ele tem uma configuração própria.

### Verificação de vulnerabilidades

O job `scan` do workflow passa o [Trivy](https://trivy.dev/) na imagem amd64 em todos os eventos, inclusive nos pull requests, que não publicam a imagem. Ele relata as vulnerabilidades `HIGH` e `CRITICAL` que já têm correção, nos pacotes do sistema e nas bibliotecas Python do venv, e as publica em dois lugares:
- no resumo da execução do workflow, em tabela;
- na aba **Security > Code scanning** do repositório (SARIF, categoria `trivy-imagem`), que guarda o histórico e fecha os alertas quando a vulnerabilidade some. PRs vindos de forks não enviam o SARIF, porque não têm a permissão `security-events: write`.

As opções ficam no `env` do workflow:
- `SCAN_SEVERITY`: severidades relatadas (padrão `HIGH,CRITICAL`);
- `SCAN_EXIT_CODE`: com `0` (padrão), o scan só relata; com `1`, o job falha quando houver achados, e o `merge` não publica a imagem. Os PRs também passam a falhar;
- `SCAN_TRIVY_VERSION`: versão do Trivy, fixa.

Vulnerabilidades aceitas vão no [`.trivyignore`](.trivyignore), uma por linha, com o motivo e uma data de expiração (`CVE-AAAA-NNNNN exp:AAAA-MM-DD`). Antes de aceitar uma vulnerabilidade de uma dependência fixada pelo GeoNode, veja se dá para forçar uma versão corrigida no `src/requirements-overrides.txt`, como foi feito com o Pillow.

**Versões fixadas por causa do incidente de 2026.** Em 19/03/2026, o projeto do Trivy teve credenciais roubadas: saiu uma release maliciosa (v0.69.4), e as tags do `aquasecurity/trivy-action` foram trocadas por código que roubava credenciais. Por isso, o workflow:
- referencia o `trivy-action` pelo SHA do commit, nunca pela tag;
- fixa a versão do Trivy, sem `latest`.

Ao atualizar, confira as releases e os advisories de [`aquasecurity/trivy`](https://github.com/aquasecurity/trivy/security/advisories) e de [`aquasecurity/trivy-action`](https://github.com/aquasecurity/trivy-action/security/advisories). Depois, troque o SHA (com a tag no comentário) e o `SCAN_TRIVY_VERSION`.

Para rodar o mesmo scan localmente, com a imagem do Trivy na mesma versão:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/.trivyignore:/.trivyignore:ro" \
  docker.io/aquasec/trivy:0.76.2 image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed \
  --ignorefile /.trivyignore ghcr.io/nds-cprm/opengeosgb-geonode:local
```

No Podman, troque o socket pelo do Podman, por exemplo `$XDG_RUNTIME_DIR/podman/podman.sock`. Ou exporte a imagem com `podman save -o img.tar` e use `trivy image --input img.tar`.

Para lançar uma versão, a partir do `main` atualizado:
1. Atualize o `version` do `src/pyproject.toml` para a versão nova, sem o `v`, e faça o commit. Numa tag `vX.Y.Z`, o workflow falha se o `pyproject.toml` declarar outra versão. Numa pré-release `vX.Y.Z-rc.N`, só o `X.Y.Z` é comparado.
2. Crie e envie a tag:

```bash
git tag -a v1.0.0 -m "OpenGeoSGB 1.0.0 (GeoNode 5.0.3)"
git push origin v1.0.0
# depois, crie a release no GitHub a partir da tag, citando a versão do GeoNode
```

## Arquitetura das imagens (amd64 e arm64)

O stack roda na arquitetura nativa do host: amd64 (Linux x86_64) ou arm64 (por exemplo, Mac com Apple Silicon e Podman). Confira com `uname -m`. O `docker-compose.opengeosgb.yml` não define `platform` nem `TARGETPLATFORM`, então cada imagem é construída e roda na arquitetura do host.

| Imagem | Base | amd64 | arm64 |
|---|---|---|---|
| `django`, `celery` | `docker.io/ndscprm/geonode-base:ubuntu-24.04-pg17` | sim | sim |
| `geonode` (nginx) | `docker.io/nginx/nginx-unprivileged:<versão>-alpine` | sim | sim |
| `geoserver` | `docker.io/library/tomcat:9.0.123-jdk17-temurin-jammy` | sim | sim |
| `letsencrypt` | `docker.io/library/alpine` | sim | sim |
| `db` (postgis) | `docker.io/postgis/postgis:<pg>-<postgis>-alpine` (padrão do Dockerfile) | sim | **não** (ver abaixo) |
| `memcached`, `redis`, `mailserver` | oficiais, sem build | sim | sim |

**PostGIS em arm64.** Em amd64, o projeto usa a imagem oficial `postgis/postgis`, padrão do `docker/docker/postgis/Dockerfile`, que só existe para amd64. Para rodar em arm64, use a `docker.io/imresamu/postgis`, uma build multiarquitetura da mesma imagem. A linha fica comentada nos `args` do serviço `db` do `docker-compose.opengeosgb.yml`. Descomente-a, de preferência num override local:

```yaml
- POSTGIS_BASE_IMAGE=docker.io/imresamu/postgis:${POSTGRES_BASE_IMAGE_VERSION}-${POSTGIS_BASE_IMAGE_VERSION}-alpine3.22
```

Sem essa linha, o build cai na `postgis/postgis` e, em arm64, falha ou sai emulado.

Em 23/11/2026, um volume `dbdata` do PG 17 criado em amd64 abriu sem erro no postgis arm64, conferido com a leitura completa das tabelas e o `bt_index_check` de todos os índices btree. Mesmo assim, copie o volume antes de trocar a arquitetura.

**Imagem publicada.** A imagem `ghcr.io/nds-cprm/opengeosgb-geonode` do GitHub Actions é multiarquitetura (amd64 e arm64, cada uma num runner nativo). O `docker pull` escolhe a variante do host. Ver "Versões e imagens publicadas".

**Forçar outra arquitetura.** Com o Docker, defina `platform: linux/<arch>` no serviço, num override local. Fora da arquitetura nativa, a imagem roda emulada (QEMU), bem mais lenta. O `podman compose` delega ao `docker-compose` e, nesse caminho, ignora o `platform` na build. Como os Dockerfiles não usam mais `FROM --platform`, no Podman construa a imagem à parte com `podman build --platform linux/<arch>`.

Se uma imagem já baixada estiver na arquitetura errada, baixe-a de novo com `podman pull --platform linux/<arch> <imagem>` (ou `docker pull`). Um `podman run --platform linux/amd64` com uma tag local também pode substituir essa tag pela versão do Docker Hub. Nesse caso, rode `geonode-docker build <serviço>` de novo.

Para conferir a arquitetura de uma imagem: `podman image inspect <imagem> --format '{{.Architecture}}'` (ou `docker image inspect`).

## Execução sem root

`django`, `celery` e `geoserver` rodam com `user: '1000:0'`: UID arbitrário e grupo 0. As imagens dão aos diretórios graváveis a permissão `g=u`, então qualquer UID do grupo 0 consegue gravar neles. Isso também deixa o stack compatível com plataformas que atribuem UIDs aleatórios, como o OpenShift.

Pontos de atenção:
- Scripts copiados para as imagens precisam de permissão de leitura, não só de execução. O `Dockerfile` usa `COPY --chmod=755`, inclusive no `COPY src/`, que exige BuildKit no Docker (padrão nas versões atuais) ou buildah no Podman. Sem isso, a cópia traz as permissões do host (700 num clone feito no macOS) e `manage.py`, o pacote `opengeosgb` e os fixtures ficam `root:root 700`: um UID que não seja o dono, como o aleatório do OpenShift, recebe `Permission denied`. O bind mount de `./src` em desenvolvimento esconde o problema.
- O GeoServer recebe `HOME=/tmp`: no Podman, o `HOME` de um UID sem entrada no `/etc/passwd` seria o `WORKDIR` (`/usr/local/tomcat/tmp`), que não é gravável.
- Volumes criados quando os containers rodavam como root podem ter arquivos que o UID 1000 não consegue gravar. Se aparecer `Permission denied`, ajuste o grupo e as permissões dentro do volume (`chgrp -R 0` e `chmod -R g=u`).

## Podman no macOS

Ajustes necessários além dos já descritos:
- O Podman sem root não publica a porta 80. Libere com `podman machine ssh "sudo sysctl -w net.ipv4.ip_unprivileged_port_start=80"` (vale até a máquina reiniciar).
- O nginx detecta o DNS pelo `/etc/resolv.conf` do container quando `RESOLVER` não está definido no `.env`. Não deixe `RESOLVER=127.0.0.11` no `.env` do Podman: esse endereço só existe no Docker, e as requisições ficam pendentes até dar timeout.
- Se os `apk add` dos builds baseados em Alpine falharem com `DNS: transient error`, o DNS da máquina do Podman travou. Reinicie-a com `podman machine stop && podman machine start` e repita o `sysctl` da porta 80.
- `docker/docker/postgis/initdb-geonode.sh` precisa estar com permissão `755` no host. Com `0700`, o usuário `postgres` não consegue executá-lo, os usuários do GeoNode não são criados e o django falha com `password authentication failed`.

## Customizações do projeto

- **Settings:** toda customização vai em `src/opengeosgb/local_settings.py`, que importa `geonode.settings`. `settings.py` só contém o que é estrutural do template.
- **Templates e estáticos:** arquivos em `src/opengeosgb/templates/` e `src/opengeosgb/static/` sobrescrevem os do GeoNode e do mapstore-client quando têm o mesmo caminho relativo.
- **Escala:** os recursos ganham o campo "Escala" no painel de informações e um filtro "Escala" no catálogo (`src/opengeosgb/metadata/`).
- **Autenticação:** login com Google, ORCID e gov.br (OpenID Connect), formulários próprios e reCAPTCHA opcional (`RECAPTCHA_ENABLED`).
- **Páginas institucionais:** flatpages em `/pages/`, editadas no admin com um editor TinyMCE restrito; o HTML é sanitizado ao salvar e ao exibir. Cada idioma é uma página separada (`/pages/sobre/` e `/pages/about/`).
- **LGPD:** faixa de consentimento de cookies; o Google Tag Manager (`GOOGLE_TAG_MANAGER_ID`) só é carregado depois do aceite. Os endereços da política de cookies e da página "Sobre" são configuráveis (`COOKIE_POLICY_URL`, `COOKIE_POLICY_URL_EN`).
- **Links legados:** `datasets/<alternate>/metadata_detail`, do GeoNode 4, redireciona para `metadata/<pk>`.
- **Celery:** o `src/celery-cmd` sobe o beat, o worker comum e o worker de harvesting. Cada worker tem o próprio limite de memória por processo filho, em KB: `CELERY__MAX_MEMORY_PER_CHILD` (padrão 200000) para o comum e `CELERY__HARVESTER_MAX_MEMORY_PER_CHILD` (padrão 500000) para o de harvesting. No template do `geonode-project` (`5.0.x`), o limite do harvester lê a variável do worker comum e fica em 200000. Aqui ele foi corrigido, então o harvester não segue mais o `CELERY__MAX_MEMORY_PER_CHILD`. Para manter o limite antigo num ambiente, defina `CELERY__HARVESTER_MAX_MEMORY_PER_CHILD` no `.env`.

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
- O projeto não tem suíte de testes própria. O `./opengeosgb-tests` roda os testes do GeoNode por grupo numa stack descartável (`./opengeosgb-tests --help`).

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
    ├── requirements.txt            # GeoNode 5.0.3 (upstream)
    ├── fixtures/
    └── opengeosgb/                 # app Django do projeto
```
