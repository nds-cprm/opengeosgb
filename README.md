# OpenGeoSGB

Instância [GeoNode](https://geonode.org/) 5 do Serviço Geológico do Brasil (SGB/CPRM): um projeto Django gerado a partir do [`geonode-project`](https://github.com/GeoNode/geonode-project) que estende o GeoNode 5.0.3 com settings, templates, URLs e fixtures próprios (app `opengeosgb`, em `src/`).

## Imagem

O workflow [`docker-image.yml`](.github/workflows/docker-image.yml) publica a imagem do Django (usada também pelo Celery) no GitHub Container Registry:

```
ghcr.io/nds-cprm/opengeosgb-geonode
```

- **Arquiteturas:** `linux/amd64` e `linux/arm64` (manifesto multiarquitetura; o `pull` baixa a variante do host).
- **Base:** `docker.io/ndscprm/geonode-base:ubuntu-24.04-pg17` (Ubuntu 24.04, Python 3.12, GDAL 3.8.4), sem root (`1000:0`) e compatível com filesystem somente leitura.
- **Conteúdo:** GeoNode 5.0.3 (upstream, sem fork) e o app `opengeosgb`. As demais imagens do stack (nginx, GeoServer, PostGIS) não são publicadas.

### Tags

| Evento | Tags publicadas |
|---|---|
| tag git `vX.Y.Z` | `X.Y.Z`, e `latest` se for a maior versão estável |
| tag git `vX.Y.Z-rc.N` | `X.Y.Z-rc.N` (pré-release, nunca `latest`) |
| push no `main` | `devel` |

As versões seguem o [SemVer](https://semver.org/lang/pt-BR/) e não acompanham as do GeoNode: a `v1.0.0` é sobre o GeoNode 5.0.3. A versão do GeoNode de cada imagem está no label `io.github.nds-cprm.opengeosgb.geonode.version`:

```bash
docker image inspect ghcr.io/nds-cprm/opengeosgb-geonode:1.0.0 \
  --format '{{ index .Config.Labels "io.github.nds-cprm.opengeosgb.geonode.version" }}'
```

### Uso

```bash
git clone --recurse-submodules https://github.com/nds-cprm/opengeosgb.git && cd opengeosgb
source opengeosgb-alias.sh               # define o comando geonode-docker
OPENGEOSGB_VERSION=1.0.0 geonode-docker pull django celery
geonode-docker up -d
```

Em desenvolvimento, `OPENGEOSGB_VERSION=local` (padrão) usa a imagem construída por `geonode-docker build`.

## Documentação

| Documento | Conteúdo |
|---|---|
| [Repositórios e stack](docs/stack.md) | Repositórios relacionados e serviços do compose |
| [Primeiros passos](docs/primeiros-passos.md) | Requisitos, arquivo `.env` e como subir o stack |
| [Versões e publicação](docs/versoes-e-publicacao.md) | Política de versões, tags, uso no compose e lançamento de releases |
| [Qualidade e segurança](docs/qualidade-e-seguranca.md) | Lint, Dependabot e Trivy |
| [Arquitetura das imagens](docs/arquitetura-imagens.md) | amd64 × arm64 e PostGIS em arm64 |
| [Execução sem root](docs/execucao-sem-root.md) | UIDs, permissões e volumes |
| [Podman no macOS](docs/podman-macos.md) | Ajustes específicos |
| [Customizações do projeto](docs/customizacoes.md) | Settings, templates, escala, autenticação, LGPD, Celery |
| [Backup e restore](docs/backup-restore.md) | Scripts de backup e restauração |
| [Desenvolvimento](docs/desenvolvimento.md) | Fluxo de desenvolvimento, testes e estrutura do repositório |
