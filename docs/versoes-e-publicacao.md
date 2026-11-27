# Versões e imagens publicadas

A imagem do Django é construída pelo workflow [`.github/workflows/docker-image.yml`](../.github/workflows/docker-image.yml) e publicada no GitHub Container Registry como `ghcr.io/nds-cprm/opengeosgb-geonode`, para `linux/amd64` e `linux/arm64` (cada uma num runner nativo), sobre a base `ubuntu-24.04-pg17`. As imagens do submódulo `docker/` (nginx, GeoServer, PostGIS, letsencrypt) não fazem parte dele.

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


## Lançar uma versão

A partir do `main` atualizado:
1. Atualize o `version` do `src/pyproject.toml` para a versão nova, sem o `v`, e faça o commit. Numa tag `vX.Y.Z`, o workflow falha se o `pyproject.toml` declarar outra versão. Numa pré-release `vX.Y.Z-rc.N`, só o `X.Y.Z` é comparado.
2. Crie e envie a tag:

```bash
git tag -a v1.0.0 -m "OpenGeoSGB 1.0.0 (GeoNode 5.0.3)"
git push origin v1.0.0
# depois, crie a release no GitHub a partir da tag, citando a versão do GeoNode
```
