# Primeiros passos

Requisitos: Docker com Compose v2, ou Podman 5+ com `podman compose` (que usa o `docker-compose` ou o `podman-compose` instalado).

```bash
git clone --recurse-submodules https://github.com/nds-cprm/opengeosgb.git
cd opengeosgb
# se já tiver clonado sem os submódulos:
git submodule update --init
```

## Arquivo `.env`

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

## Subir o stack

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
