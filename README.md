# OpenGeoSGB

Instância [GeoNode](https://geonode.org/) 5 do Serviço Geológico do Brasil (SGB/CPRM).

Este repositório é um projeto Django gerado a partir do template [`geonode-project`](https://github.com/GeoNode/geonode-project). Ele estende o GeoNode com settings, templates, URLs e fixtures próprios (app `opengeosgb`, em `src/`) e traz a configuração Docker do stack completo.

## Repositórios relacionados

| Repositório | Papel |
|---|---|
| [`GeoNode/geonode`](https://github.com/GeoNode/geonode) (branch `5.0.x`) | Núcleo do GeoNode, instalado via `src/requirements.txt`. |
| [`nds-cprm/geonode`](https://github.com/nds-cprm/geonode) | Fork do núcleo, para mudanças que não dá para fazer por extensão (modelos, upload). O catálogo ISO 19115-3, que antes vivia no branch `iso19115-3_2018-support`, agora é o app [`opengeosgb.catalogue`](#catálogo-e-metadados-opengeosgbcatalogue). |
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
- **Metadados e CSW:** o XML de metadados sai em ISO 19115-3 (2018) por padrão, e o CSW só entrega datasets aprovados, publicados e com metadados completos. Veja [Catálogo e metadados](#catálogo-e-metadados-opengeosgbcatalogue).
- **Escala:** os recursos ganham o campo "Escala" no painel de informações e um filtro "Escala" no catálogo (`src/opengeosgb/metadata/`).
- **Autenticação:** login com Google, ORCID e gov.br (OpenID Connect), formulários próprios e reCAPTCHA opcional (`RECAPTCHA_ENABLED`).
- **Páginas institucionais:** flatpages em `/pages/`, editadas no admin com um editor TinyMCE restrito; o HTML é sanitizado ao salvar e ao exibir. Cada idioma é uma página separada (`/pages/sobre/` e `/pages/about/`).
- **LGPD:** faixa de consentimento de cookies; o Google Tag Manager (`GOOGLE_TAG_MANAGER_ID`) só é carregado depois do aceite. Os endereços da política de cookies e da página "Sobre" são configuráveis (`COOKIE_POLICY_URL`, `COOKIE_POLICY_URL_EN`).
- **Links legados:** `datasets/<alternate>/metadata_detail`, do GeoNode 4, redireciona para `metadata/<pk>`.

## Catálogo e metadados (`opengeosgb.catalogue`)

O app `opengeosgb.catalogue`, em `src/opengeosgb/catalogue/`, substitui partes do módulo `geonode.catalogue` sem mudar o núcleo. Ele cuida de três coisas:

- o formato do XML de metadados gravado em cada recurso (ISO 19115-3 ou ISO 19139);
- o endpoint CSW `/catalogue/csw`, servido pelo pycsw;
- a validação desse XML contra o XSD oficial.

O GeoNode 5.0.x só conhece o ISO 19139 e não tem um ponto de extensão para trocar o formato. Antes, o suporte a ISO 19115-3 exigia um fork do núcleo (branch `iso19115-3_2018-support`). Com este app, o projeto passa a usar o GeoNode do upstream.

### Configuração

O app entra no `INSTALLED_APPS` pelo `local_settings.py`, que também define os valores abaixo. Todos podem ser trocados no `.env`.

| Variável | Padrão | Efeito |
|---|---|---|
| `CATALOGUE_DEFAULT_FORMAT` | `ISO19115-3_2018` | Formato do XML gravado e devolvido pelo catálogo: `ISO19115-3_2018` ou `ISO` (ISO 19139). Um valor inválido impede o Django de iniciar. |
| `CATALOG_METADATA_TEMPLATE` | template do formato | Template usado para gerar o XML. Só mude se for usar um template próprio, com a raiz do mesmo formato. |
| `CATALOGUE_ENGINE` | `opengeosgb.catalogue.backends.pycsw_local` | Backend do catálogo. Com outro valor, o formato e as correções do app deixam de valer, e o `manage.py check` avisa. |
| `CSW_MIN_METADATA_COMPLETENESS` | `60` | Completude mínima dos metadados (em %) para um dataset aparecer no CSW. |
| `PYCSW_DOMAINQUERYTYPE` | `list` | Resposta do `GetDomain`: `list` (cada valor com a contagem de registros) ou `range` (só o menor e o maior valor). |

A identificação do serviço (título, provedor, contato) continua em `PYCSW["CONFIGURATION"]["metadata"]`, no `local_settings.py`.

### Como o XML de metadados é gerado

O GeoNode gera o XML e o grava no campo `metadata_xml` do recurso. O pycsw lê esse campo para responder ao CSW. O caminho é este:

1. Ao salvar um dataset ou documento, o GeoNode chama `catalogue_post_save`. O mesmo acontece no `regenerate_xml`, no `set_all_datasets_metadata` e quando o GeoServer atualiza os links do recurso.
2. O backend do app (`backends/pycsw_local.py`) grava `csw_typename` e `csw_schema` de acordo com o formato: `mdb:MD_Metadata` para ISO 19115-3 e `gmd:MD_Metadata` para ISO 19139. O editor de metadados salva o recurso sem passar por esse caminho, então um `pre_save` (`signals.py`) faz o mesmo.
3. O XML é gerado com o template do formato e gravado em `metadata_xml`. Um XML enviado pelo usuário com a opção de preservar continua como veio, e `csw_typename` segue o formato desse XML.
4. O GeoNode cria um link de metadados para cada formato que o catálogo oferece, inclusive o ISO 19115-3.

Os campos `csw_typename` e `csw_schema` precisam bater com o XML gravado. O perfil `iso19115p3` do pycsw só devolve o XML como está quando `csw_typename` é `mdb:MD_Metadata`, e o perfil `apiso` (ISO 19139) só quando é `gmd:MD_Metadata`. Nos outros casos, o pycsw monta o registro a partir das colunas do banco.

### O que o CSW entrega

O endpoint `/catalogue/csw` usa uma view própria (`views.py`). Para cada requisição, o filtro é montado assim, com as cláusulas sempre unidas por `AND`:

- o registro tem UUID;
- o usuário tem permissão de ver o recurso (sem login, vale a do usuário anônimo);
- o recurso é um dataset aprovado, publicado e com completude de metadados acima de `CSW_MIN_METADATA_COMPLETENESS` (`filters.py`);
- se `GROUP_PRIVATE_RESOURCES` estiver ligado, o recurso não pertence a um grupo privado de que o usuário não participa (não vale para superusuários).

A completude é calculada em SQL, reproduzindo a propriedade `ResourceBase.metadata_completeness` do GeoNode.

O filtro vale para todas as operações (`GetRecords`, `GetRecordById`, `GetDomain`) e para qualquer usuário, inclusive administradores. Ele não afeta a geração do XML: todo recurso tem `metadata_xml`, mesmo os que ficam fora do CSW.

Formatos que o CSW devolve (parâmetro `outputschema`):

| `outputschema` | Resultado |
|---|---|
| `http://standards.iso.org/iso/19115/-3/mdb/2.0` | ISO 19115-3. Sai o XML gravado, quando ele está nesse formato. |
| `http://www.isotc211.org/2005/gmd` | ISO 19139, montado pelo pycsw a partir das colunas quando o XML gravado é ISO 19115-3. |
| `http://www.opengis.net/cat/csw/2.0.2` e outros | Dublin Core, ebRIM, FGDC etc., montados pelo pycsw. |

Exemplos:

```
/catalogue/csw?service=CSW&version=2.0.2&request=GetCapabilities
/catalogue/csw?service=CSW&version=2.0.2&request=GetRecordById&id=<uuid>&elementsetname=full&outputschema=http://standards.iso.org/iso/19115/-3/mdb/2.0
/catalogue/csw?service=CSW&version=2.0.2&request=GetDomain&propertyname=dc:title
```

### Diferenças em relação ao catálogo do GeoNode 5.0.x

Além do formato configurável, o app corrige estes problemas do núcleo:

| Problema no GeoNode 5.0.x | No app |
|---|---|
| A configuração do pycsw é uma cópia rasa. A view altera o filtro de permissão num dicionário compartilhado do módulo, e com workers em threads uma requisição pode usar o filtro de outro usuário. | A configuração é montada de novo a cada uso (`config.py`), com mescla profunda. |
| Os padrões do `pycsw_local` vencem os settings, inclusive em `profiles`, o que impede ligar o perfil `iso19115p3`. | Os settings vencem, e os perfis `apiso`, `ebrim` e `iso19115p3` estão sempre ligados. |
| Para o usuário logado, o filtro vira `(...) OR (id IN ...)`. Os filtros de grupo e de `ALTERNATES_ONLY`, acrescentados depois, deixam de valer para ele. | Cláusulas unidas só por `AND`, entre parênteses. |
| A view redireciona quando `CATALOGUE_ENGINE` não é exatamente o `pycsw_local` do núcleo. | A view aceita o backend do app e o do núcleo. |
| Todo `GetDomain` volta vazio: o django-polymorphic falha nas agregações do repositório (`AttributeError: 'NoneType' object has no attribute 'name'`), e o pycsw esconde o erro. | Repositório próprio (`backends/pycsw_repository.py`), que consulta sem o polymorphic. |
| O backend guarda o objeto `Catalogue` na classe, compartilhado entre instâncias, e o `search_records` chama `.items()` numa lista. | O `Catalogue` fica na instância, e a busca foi corrigida. |

### Templates

Os templates ficam em `templates/opengeosgb_catalogue/`, com nomes próprios. Um `catalogue/full_metadata.xml` dentro do app perderia para o do núcleo, por causa da ordem dos apps no `INSTALLED_APPS`.

- `full_metadata_iso19115-3.xml`: ISO 19115-3 (`mdb` 2.0), válido contra o XSD. O `mdb:contact` é obrigatório no padrão, então um recurso sem contatos usa o dono como `pointOfContact`.
- `_iso19115-3_responsibility.xml`: um contato (`cit:CI_Responsibility`), usado em `mdb:contact` e em `mri:pointOfContact`.
- `full_metadata_iso19139.xml`: cópia do template ISO 19139 do GeoNode 5.0.x, mais o bloco de escala.

Os dois formatos incluem a escala do recurso (o campo esparso `scale` do opengeosgb) em `spatialResolution/equivalentScale`. Outros campos esparsos podem ser usados nos templates como `metadata.<campo>`.

### Validação contra o XSD

`validation.py` valida o XML contra o schema oficial do formato. Hoje só o ISO 19115-3 tem schema configurado (`mdb/2.0/mdb.xsd`).

Os schemas ficam em `schemas/`: são 131 arquivos XSD de isotc211.org, opengis.net (GML) e w3.org. É uma cópia local, para a validação não depender de rede. O servidor da ISO é lento e às vezes não responde a tempo. Os arquivos espelham `host/caminho` das URLs originais, com os `schemaLocation` reescritos como caminhos relativos. Não edite esses arquivos à mão: para atualizá-los, rode `fetch_metadata_schemas`.

A validação confere a estrutura (ordem dos elementos, elementos obrigatórios, tipos e atributos). Ela não confere os valores de codelist, como `CI_RoleCode` e `MD_ScopeCode`.

### Comandos

| Comando | Para que serve |
|---|---|
| `python manage.py regenerate_xml [-i ID] [-l NOME] [-d]` | Comando do GeoNode. Regera o XML e os links de metadados. Sem filtros, processa todos os recursos. Rode depois de trocar `CATALOGUE_DEFAULT_FORMAT`; até lá, os registros antigos continuam no formato anterior. |
| `python manage.py validate_metadata_xml [--id ID] [--max-errors N]` | Valida o `metadata_xml` gravado nos recursos e lista os erros de cada um. Termina com código 1 se algum XML for inválido. Recursos em formato sem XSD são contados como ignorados. |
| `python manage.py fetch_metadata_schemas [--cache DIR]` | Baixa de novo os XSD para `schemas/`. O `--cache` guarda os arquivos originais e evita baixá-los outra vez. |

Para trocar o formato num ambiente:

```bash
# no .env: CATALOGUE_DEFAULT_FORMAT=ISO19115-3_2018 (ou ISO), depois reinicie django e celery
geonode-docker exec django python manage.py regenerate_xml
geonode-docker exec django python manage.py validate_metadata_xml
```

### Testes

```bash
geonode-docker exec django python manage.py test opengeosgb.catalogue
```

Os testes precisam de PostGIS. Eles cobrem:

- a geração do XML nos dois formatos, com a escala;
- a troca de formato pelo editor de metadados;
- as respostas do CSW em ISO 19115-3 e ISO 19139;
- o `GetDomain`;
- o filtro de permissões;
- a configuração do pycsw;
- a validação do XML ISO 19115-3 contra o XSD;
- a inclusão de um dataset fictício completo (um mapa geológico), criado pelo `resource_manager.create` como no fluxo real.

O dataset fictício é montado por `create_fictitious_dataset()`, em `tests.py`. Ele preenche tudo o que o template usa: categoria, licença, restrições, DOI, edição, palavras-chave livres, de tesauro e de região, contatos com perfil completo, links de download e OGC, escala e linhagem. Os testes com ele verificam:

- o conteúdo do XML nos dois formatos;
- a validade contra o XSD em três variantes: vetor com licença `light`, vetor com licença `verbose` e raster;
- que o CSW entrega esse dataset e omite um rascunho não aprovado.

Só a sincronização com o GeoServer é substituída por um mock, porque não há GeoServer nos testes.

Rode os testes sempre que mudar o template ISO 19115-3. Para cobrir um campo novo do template, acrescente-o ao dataset fictício.

### Ao atualizar o GeoNode

Partes do app são cópias adaptadas do núcleo. Compare cada uma com o original da nova versão:

| No app | No GeoNode |
|---|---|
| `backends/pycsw_local.py` (`get_record`, `search_records`, `_csw_local_dispatch`) | `geonode/catalogue/backends/pycsw_local.py` |
| `backends/pycsw_repository.py` (`query_domain`) | `geonode/catalogue/backends/pycsw_plugin.py` |
| `views.py` (`csw_global_dispatch`) | `geonode/catalogue/views.py` |
| `filters.py` (`with_metadata_completeness`) | `ResourceBase.metadata_completeness`, em `geonode/base/models.py` |
| `templates/opengeosgb_catalogue/full_metadata_iso19139.xml` | `geonode/catalogue/templates/catalogue/full_metadata.xml` |

Se o upstream corrigir algum dos problemas da tabela de diferenças, a cópia correspondente pode ser removida.

### Arquivos

```
src/opengeosgb/catalogue/
├── apps.py               # registro do app, pre_save e checks do Django
├── constants.py          # nomes dos formatos, templates e perfis do pycsw (importável nos settings)
├── formats.py            # tabela de formatos e regra de csw_typename/csw_schema
├── config.py             # configuração do pycsw, montada a cada uso
├── backends/
│   ├── pycsw_local.py    # backend (CATALOGUE_ENGINE)
│   └── pycsw_repository.py  # repositório do pycsw com o GetDomain corrigido
├── views.py, urls.py     # endpoint /catalogue/csw
├── filters.py            # critérios do conjunto entregue pelo CSW
├── signals.py            # csw_typename/csw_schema no save
├── validation.py         # validação contra o XSD
├── schemas/              # cópia local dos XSD (gerada por fetch_metadata_schemas)
├── management/commands/  # fetch_metadata_schemas, validate_metadata_xml
├── templates/opengeosgb_catalogue/
└── tests.py
```

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
- Testes: só o app de catálogo tem suíte própria (`python manage.py test opengeosgb.catalogue`, ver [Testes](#testes)). Os testes do núcleo ficam no repositório do GeoNode.

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
    ├── requirements.txt            # GeoNode (branch 5.0.x)
    ├── fixtures/
    └── opengeosgb/                 # app Django do projeto
        └── catalogue/              # catálogo CSW e formatos de metadados
```
