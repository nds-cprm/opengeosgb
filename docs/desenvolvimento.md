# Desenvolvimento

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
