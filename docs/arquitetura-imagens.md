# Arquitetura das imagens (amd64 e arm64)

O stack roda na arquitetura nativa do host: amd64 (Linux x86_64) ou arm64 (por exemplo, Mac com Apple Silicon e Podman). Confira com `uname -m`. O `docker-compose.opengeosgb.yml` não define `platform` nem `TARGETPLATFORM`, então cada imagem é construída e roda na arquitetura do host.

| Imagem | Origem | Base | amd64 | arm64 |
|---|---|---|---|---|
| `django`, `celery` | `ghcr.io/nds-cprm/opengeosgb-geonode` (GitHub Actions, multiarquitetura) ou build local (tag `local`) | `docker.io/ndscprm/geonode-base:ubuntu-24.04-pg17` | sim | sim |
| `geonode` (nginx) | build local (`docker/docker/nginx`) | `docker.io/nginx/nginx-unprivileged:<versão>-alpine` | sim | sim |
| `geoserver` | build local (`docker/docker/geoserver`) | `docker.io/library/tomcat:9.0.123-jdk17-temurin-jammy` | sim | sim |
| `letsencrypt` | build local (`docker/docker/letsencrypt`) | `docker.io/library/alpine` | sim | sim |
| `db` (postgis) | build local (`docker/docker/postgis`) | `docker.io/postgis/postgis:<pg>-<postgis>-alpine` (padrão do Dockerfile) | sim | **não** (ver abaixo) |
| `memcached`, `redis`, `mailserver` | imagens oficiais, sem build | — | sim | sim |

Nas imagens de build local, as colunas amd64 e arm64 dizem se a base existe para a arquitetura. Na imagem do GHCR, dizem se a variante é publicada.

**PostGIS em arm64.** Em amd64, o projeto usa a imagem oficial `postgis/postgis`, padrão do `docker/docker/postgis/Dockerfile`, que só existe para amd64. Para rodar em arm64, use a `docker.io/imresamu/postgis`, uma build multiarquitetura da mesma imagem. A linha fica comentada nos `args` do serviço `db` do `docker-compose.opengeosgb.yml`. Descomente-a, de preferência num override local:

```yaml
- POSTGIS_BASE_IMAGE=docker.io/imresamu/postgis:${POSTGRES_BASE_IMAGE_VERSION}-${POSTGIS_BASE_IMAGE_VERSION}-alpine3.22
```

Sem essa linha, o build cai na `postgis/postgis` e, em arm64, falha ou sai emulado.

Em 23/11/2026, um volume `dbdata` do PG 17 criado em amd64 abriu sem erro no postgis arm64, conferido com a leitura completa das tabelas e o `bt_index_check` de todos os índices btree. Mesmo assim, copie o volume antes de trocar a arquitetura.

**Imagem publicada.** A imagem do django e do celery, `ghcr.io/nds-cprm/opengeosgb-geonode`, é publicada pelo GitHub Actions como um manifesto multiarquitetura (amd64 e arm64). O `docker pull` (ou `podman pull`) baixa a variante do host, sem precisar de `--platform`.
- Cada arquitetura é construída num runner nativo do GitHub (`ubuntu-24.04` e `ubuntu-24.04-arm`), sem emulação, sobre a variante da base com a mesma arquitetura.
- Só é publicada a variante pg17 da base.
- O Trivy só verifica a variante amd64.

As outras imagens do stack (nginx, geoserver, postgis, letsencrypt) não são publicadas pelo projeto: elas continuam sendo construídas localmente, na arquitetura do host. Para conferir as arquiteturas de uma tag publicada:

```bash
docker buildx imagetools inspect ghcr.io/nds-cprm/opengeosgb-geonode:1.0.0
```

Ver também [Versões e imagens publicadas](versoes-e-publicacao.md).

**Forçar outra arquitetura.** Com o Docker, defina `platform: linux/<arch>` no serviço, num override local. Fora da arquitetura nativa, a imagem roda emulada (QEMU), bem mais lenta. O `podman compose` delega ao `docker-compose` e, nesse caminho, ignora o `platform` na build. Como os Dockerfiles não usam mais `FROM --platform`, no Podman construa a imagem à parte com `podman build --platform linux/<arch>`.

Se uma imagem já baixada estiver na arquitetura errada, baixe-a de novo com `podman pull --platform linux/<arch> <imagem>` (ou `docker pull`). Um `podman run --platform linux/amd64` com uma tag local também pode substituir essa tag pela versão do Docker Hub. Nesse caso, rode `geonode-docker build <serviço>` de novo.

Para conferir a arquitetura de uma imagem: `podman image inspect <imagem> --format '{{.Architecture}}'` (ou `docker image inspect`).
