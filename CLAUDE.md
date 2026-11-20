# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Idioma

Use **português do Brasil** em respostas, comentários, mensagens de commit e documentação deste projeto.

## O que é

OpenGeoSGB é a instância GeoNode do Serviço Geológico do Brasil (SGB/CPRM). Ele foi gerado a partir do template `geonode-project` e é um projeto Django fino (app `opengeosgb`, em `src/`) que estende o GeoNode 5 por meio de settings, templates, URLs e fixtures. Este é o repositório principal. Os diretórios irmãos são dependências:

- `../geonode`: clone do GeoNode (remotos `origin` = fork `nds-cprm/geonode`, `upstream` = `GeoNode/geonode`). O `src/requirements.txt` instala o branch `5.0.x` do upstream; o catálogo ISO 19115-3, que antes exigia o branch `iso19115-3_2018-support` do fork, agora vive no app `opengeosgb.catalogue`. Mudanças que não dá para fazer por extensão (modelos, upload) vão para o fork, num branch a partir do `5.0.x`.
- `../geonode-mapstore-client`: frontend (React/MapStore), uma dependência do GeoNode. Os templates sobrescritos ficam em `src/opengeosgb/templates/geonode-mapstore-client/`.
- `../geonode-project`: template de origem deste projeto. Use-o como referência para comparar com a versão upstream.
- `docker/`: submódulo git (`nds-cprm/geonode-docker`, branch `opengeosgb`) com os Dockerfiles do nginx, GeoServer, geoserver_data, PostGIS e letsencrypt.

## Comandos

O stack inteiro roda em Docker. O compose base (`docker-compose.yml`) é sempre combinado com o override `docker-compose.opengeosgb.yml`, que monta `./src` em `/usr/src/project`, expõe as portas e constrói as imagens a partir do submódulo `docker/`:

```bash
git submodule update --init            # necessário para os builds do docker/
source opengeosgb-alias.sh             # define: geonode-docker = docker compose -f docker-compose.yml -f docker-compose.opengeosgb.yml
geonode-docker build
geonode-docker up -d
geonode-docker exec django python manage.py <cmd>
geonode-docker logs -f django celery
```

- Os serviços leem `.env` (`env_file`). Os arquivos `.env.dev`, `.env.prod`, `.env.p3m`, `.env.localhost` e `.env.restoreprod` são variantes por ambiente, e `.env.sample` é a referência das variáveis. Para gerar um `.env` novo: `python create-envfile.py --env_type dev|test|prod --hostname ...`.
- O override `docker-compose.opengeosgb-restore.yml` serve para restaurar backups de produção. O diretório `./draft/br` é montado como `/backup_restore`, e os scripts ficam em `src/opengeosgb/br/`.
- O container de dev pode ser aberto pelo `.devcontainer/` (serviço `django`, workspace `/usr/src/project`).
- A inicialização do container é feita por `src/entrypoint.sh` → `invoke` (`src/tasks.py`: `waitfordbs`, `update`, `migrations`, `prepare`, `fixtures`, `collectstatic`, `initialized`). O task `fixtures` carrega os fixtures padrão do GeoNode e depois os listados em `PROJECT_FIXTURES`.

Lint: `flake8` com a configuração de `.flake8` (max-line-length 200; `F403`/`F405` ignorados por causa dos `import *` nos settings).

O projeto não tem suíte de testes própria. Os testes do núcleo ficam em `../geonode` (veja o `CLAUDE.md` de lá, se existir).

## Arquitetura

**Cadeia de settings.** `opengeosgb/settings.py` faz `from opengeosgb.local_settings import *`, e este faz `from geonode.settings import *`. Se o import de `local_settings` falhar, ele cai direto em `geonode.settings`. Logo, **toda customização de settings vai em `local_settings.py`**: flatpages, `LANGUAGES`, formulários de conta, provedores sociais, identificação/contato do pycsw e o Google Tag Manager. Já `settings.py` só cuida do que é estrutural do template (`STATICFILES_DIRS`, `LOCALE_PATHS` e `TEMPLATES` com prioridade para os diretórios locais, `ROOT_URLCONF`, `PROJECT_FIXTURES`). Quase tudo vem de variáveis de ambiente lidas pelo `geonode.settings`. Por exemplo, `CATALOGUE_DEFAULT_FORMAT=ISO19115-3_2018` troca o perfil de metadados (ISO 19139 ↔ ISO 19115-3); essa lógica vive no app `opengeosgb.catalogue`, configurado em `local_settings.py`.

**Configuração do client em tempo de execução.** `templates/geonode-mapstore-client/_geonode_config.html` (função `overrideLocalConfig`) ajusta o `localConfig.json` do client antes de ele ser usado:
- a coluna "Descrição" da lista do catálogo passa a ler `raw_abstract` (ver pendência [mapstore-client]);
- todas as datas configuradas (`type: "date"`) passam a usar o formato `L HH:mm`, a data numérica do idioma mais a hora em 24h (06/11/2026 23:42 em pt, 11/06/2026 23:42 em en).

A aba de informações do painel ganha a linha "Escala", depois de "Regiões" e só quando o recurso tem escala. Para isso:
- `opengeosgb/metadata/serializers.py` acrescenta o campo `scale` (o campo esparso) aos serializers de recursos do GeoNode (`ResourceBase`, `Dataset`, `Map`, `Document` e `GeoApp`) no `ready()` do app;
- o campo é diferido: só é calculado com `include[]=scale` ou com um preset que o inclua, por isso não pesa nas listagens;
- o `apps.py` o acrescenta ao preset `viewer_common`, usado pelo painel;
- o rótulo vem de `static/opengeosgb/translations/data.<locale>.json`, as traduções do client próprias do projeto, acrescentadas ao `MAPSTORE_TRANSLATIONS_PATH` em `local_settings.py`.

A barra de filtros do catálogo ganha o filtro "Escala", depois de "Região" (inserido pelo `overrideLocalConfig`). Ele é sustentado por `opengeosgb/metadata/facets.py`:
- `ScaleFacetProvider` é a facet `scale` da API `/api/v2/facets`, registrada em `FACET_PROVIDERS` no `local_settings.py`. Ela lista as escalas usadas e a contagem de recursos de cada uma.
- `ScaleFilter` filtra a API de recursos pelo parâmetro `scale=<denominador>`, que pode se repetir. O `apps.py` o acrescenta ao `ResourceBaseViewSet.filter_backends`, e a API de facets usa esse mesmo filtro nas contagens.

O filtro padrão do `dynamic_rest` (`filter{…}`) não funciona para campos esparsos, por isso o parâmetro próprio.

O painel de propriedades (`ResourceDetails`) não mescla configuração parcial. Por isso, nas páginas sem `cfg.tabs`, o override fornece as abas completas a partir de `templates/opengeosgb/resource_details_tabs.json`, uma cópia das abas padrão do client 5.0.3 extraída de `resource-details-plugin.*.chunk.js`. **Ao atualizar o geonode-mapstore-client, compare esse JSON com o padrão da nova versão.**

**Sobrescrita de templates.** `src/opengeosgb/templates/` vem primeiro em `TEMPLATES[0]["DIRS"]` (o `apps.py` também o insere no `ready()`). Para customizar uma página, crie um arquivo com o mesmo caminho relativo do template original do GeoNode ou do mapstore-client (por exemplo `geonode-mapstore-client/snippets/hero.html` ou `geonode_base.html`). Os arquivos estáticos seguem a mesma lógica com `src/opengeosgb/static/`. Ajustes de CSS sobre o tema do client ficam em `static/opengeosgb/css/opengeosgb.css`, carregado no `head.html` do client. Hoje esse arquivo tem só o título dos cards do catálogo, com até duas linhas e altura fixa de duas linhas. Use seletores mais específicos que os do tema (prefixo `.msgapi`), porque o tema do client pode ser carregado depois.

**URLs.** `opengeosgb/urls.py` importa `geonode.urls.urlpatterns` e acrescenta as rotas próprias: flatpages em `/pages/` e a rota legada do GeoNode 4 `datasets/<alternate>/metadata_detail`, que redireciona (301) para `metadata/<pk>` (`views.legacy_metadata_detail`). Ela existe para manter vivos os links antigos do P3M.

**Autenticação.** Os formulários do allauth são trocados por `opengeosgb.account.forms` (variantes GovBR, com ou sem reCAPTCHA conforme `RECAPTCHA_ENABLED`). Os provedores sociais são Google, ORCID e OpenID Connect (gov.br). O `GovBRExtractor` (`account/profileextractors.py`) mapeia os claims do gov.br para o perfil do usuário.

**Context processors.** `opengeosgb.context_processors.google_tag_manager_snippet` expõe `GOOGLE_TAG_MANAGER_ID` aos templates, mas só quando o valor casa com `^GTM-[A-Z0-9]{4,10}$`. `site_pages` expõe `COOKIE_POLICY_URL` e `ABOUT_PAGE_URL` no idioma da requisição. Esses endereços são usados no aviso de cookies e no rodapé (`templates/geonode-mapstore-client/snippets/footer.html`, cópia do snippet do client 5.0.3). O rodapé tem os links Sobre, Política de cookies e Preferências de cookies, este último reabrindo o aviso. O `ABOUT_PAGE_URLS` segue o mesmo padrão descrito a seguir para a política de cookies. O valor vem de `COOKIE_POLICY_URLS` (em `local_settings.py`), que mapeia `pt` para `/pages/politica-de-cookies/` e `en` para `/pages/cookie-policy/`. Os dois endereços são configuráveis por `COOKIE_POLICY_URL` e `COOKIE_POLICY_URL_EN`. Flatpages não têm tradução: cada idioma é uma página separada, com um link no topo para a outra versão (`/pages/sobre/` e `/pages/about/`, `/pages/politica-de-cookies/` e `/pages/cookie-policy/`).

**Aviso de cookies (LGPD) e Google Tag Manager.** `templates/opengeosgb/snippets/cookie_consent.html` é incluído no `<head>` de `templates/base.html` (páginas do Django) e de `templates/geonode-mapstore-client/snippets/head.html` (páginas do client). Ele roda uma única vez por página, mesmo quando incluído nos dois.
- Mostra uma faixa no rodapé com "Rejeitar cookies opcionais", "Aceitar cookies" e o link para a política. A faixa fica num `<template>` e é inserida no `<body>` por JavaScript.
- A escolha fica no cookie `opengeosgb_cookie_consent` (`accepted` ou `rejected`, 1 ano).
- **O Google Tag Manager só é carregado depois do aceite**, por isso não existe mais snippet de GTM carregado diretamente. Ao recusar, os cookies `_ga`, `_gid`, `_gat` e `_gcl` são apagados.
- Qualquer link para `#preferencias-de-cookies` reabre a faixa. A página de política usa esse link, e ele é aceito pela sanitização das flatpages.
- Para atender ao LGPD, o `<noscript>` do GTM não é usado: sem JavaScript não há como registrar consentimento.

**Fixtures do projeto.** `src/fixtures/opengeosgb/` contém licenças e regiões do Brasil, além do tesauro `labels-i18n.rdf` (rótulos pt do editor de metadados do GeoNode: títulos e descrições dos campos como sobrescritas `<campo>__ovr`/`<campo>__descr__ovr`, e mensagens `metadata_*` do editor). Ele não é carregado automaticamente; para carregar ou atualizar em um ambiente:

```bash
geonode-docker exec django python manage.py thesaurus load -i labels-i18n \
  -f /usr/src/project/fixtures/opengeosgb/labels-i18n.rdf --action update   # use --action create na primeira carga
```

O editor guarda os rótulos em cache, mas invalida o cache sozinho quando o tesauro muda, então não é preciso reiniciar.

O arquivo `opengeosgb-flatpages.json` traz as flatpages institucionais: Sobre/About e Política de cookies/Cookie policy, ids 10 a 13. As imagens enviadas dessas páginas ficam em `flatpages_media/<id>/`. Os ids são fixos porque os endereços das imagens (`/uploaded/flatpages/<id>/…`) dependem deles. Carregar o fixture sobrescreve flatpages que já tenham esses ids. Para carregar em um ambiente:

```bash
geonode-docker exec django python manage.py loaddata /usr/src/project/fixtures/opengeosgb/opengeosgb-flatpages.json
geonode-docker exec django bash -c 'mkdir -p /mnt/volumes/statics/uploaded/flatpages && cp -r /usr/src/project/fixtures/opengeosgb/flatpages_media/* /mnt/volumes/statics/uploaded/flatpages/'
```

Para regerar o fixture depois de editar as páginas: `python manage.py dumpdata flatpages.flatpage --pks 10,11,12,13 --indent 2`, copiando também as pastas `uploaded/flatpages/10` e `12`.

**Handler de metadados do projeto.** `opengeosgb/metadata/handlers.py` define o `OptionsI18nHandler`, registrado no `ready()` do app (`apps.py`) via `metadata_manager.add_handler()`. Ele roda depois dos handlers do GeoNode e não é dono de nenhum campo. Sua função é traduzir, com `pgettext` e um contexto por campo, as opções que o GeoNode monta sem `gettext`: idioma, restrições e tipo de representação espacial. As traduções ficam no `django.po`, em uma seção própria com `msgctxt`. No mesmo `ready()`, o handler `region` do GeoNode é substituído por `RegionsI18nHandler`, que aponta o campo de regiões para o autocomplete próprio (`opengeosgb/metadata/views.py`, rota `opengeosgb_metadata_autocomplete_regions`) e traduz os rótulos das regiões salvas. Só regiões de nível 0 a 3 (global, continentes, sub-regiões e países) são traduzidas, com o contexto `metadata region`. Os estados (nível 4) e municípios (nível 5) brasileiros já estão em português e ficam fora do `.po`. A regra está em `opengeosgb/metadata/i18n.py`. O handler `base` também é substituído, por `BaseFormHandler`, que muda duas coisas no formulário. O campo "date" passa a ser editado só como data, e ao salvar o horário já gravado é mantido. O campo "supplemental_information" deixa de ter texto padrão. Quando o editor manda esse campo nulo ou ausente, ele é gravado como texto vazio, porque a coluna é `NOT NULL` no GeoNode. Tornar o campo nulo de verdade exige mudar o modelo no fork.

**Campos extras do editor.** Campos que não existem no `ResourceBase` são declarados em `opengeosgb/metadata/fields.py`. Hoje só existe `scale`, opcional. Ele é um objeto `{id: denominador, label: "1:250.000"}`, porque o editor só oferece autocomplete para objetos e listas. As sugestões vêm de `opengeosgb/metadata/scales.py`: as escalas comuns de `COMMON_SCALES` mais as já usadas em outros recursos. O que o usuário digita também vira opção, o que substitui o `creatable`, que o client não suporta em seleção única. O `SparseFieldsUiHandler` liga o autocomplete ao campo e apaga o `{}` que o GeoNode grava quando o campo é limpo. Eles são registrados como campos esparsos do GeoNode (`sparse_field_registry`, tabela `SparseField`) no `ready()` do app, sem precisar de migração. Os rótulos em português vão no tesauro `labels-i18n` (`<campo>__ovr` e `<campo>__descr__ovr`), que precisa ser recarregado com `--action update` depois de mudanças. Campos esparsos não saem sozinhos no XML ISO/CSW: os templates do app `opengeosgb.catalogue` (`catalogue/templates/opengeosgb_catalogue/full_metadata_*.xml`) precisam usá-los via `metadata.<campo>`, contexto que o `csw_gen_xml` já fornece. Hoje só a escala sai, como `spatialResolution/equivalentScale/…/denominator`.

**Página de visualização de metadados.** As rotas `/metadata/<pk>` e `/metadata/<pk>/embed` (a segunda é usada em iframe pelo plugin `MetadataViewer` do client) foram substituídas pelas views de `opengeosgb/metadata/views.py`. Elas são inseridas no início de `urlpatterns` em `urls.py` e mantêm os mesmos nomes de rota. Diferente da view original do client, verificam a permissão de leitura do recurso (`base.view_resourcebase`). O conteúdo é montado em `opengeosgb/metadata/page.py`:
- seções fixas (`SECTIONS`); campos preenchidos que não estão em nenhuma seção vão para "Outras informações";
- extensão geográfica e sistema de referência;
- contatos agrupados por pessoa;
- dicionário de dados (atributos do dataset);
- citação;
- links de distribuição agrupados;
- registro de metadados.

Na distribuição, os arquivos originais (assets do upload) ficam separados dos downloads gerados pelo GeoServer. O link de GeoPackage não é criado pelo GeoNode: a página monta esse link a partir do download WFS em CSV, trocando o `outputFormat` para `geopkg`. Isso depende das extensões `excel` e `geopkg-output` do GeoServer, instaladas pelo `ARG GEOSERVER_EXTENSIONS` no Dockerfile do submódulo `docker/docker/geoserver`. Datas são formatadas no Python, no formato curto do idioma ativo. A apresentação fica no snippet sobrescrito `templates/geonode-mapstore-client/snippets/metadata_view.html`, usado pelos dois templates do client, mais `templates/opengeosgb/snippets/metadata_item.html`. Os títulos dos campos vêm do schema, já traduzidos, e por isso não passam por `{% trans %}`. Passar causaria tradução dupla: "Data" virava "Dados".

**Flatpages (app `opengeosgb.flatpages_editor`, rótulo `opengeosgb_flatpages`).** Este app fica em `src/opengeosgb/flatpages_editor/` e entra no `INSTALLED_APPS` pelo `local_settings.py`, logo depois de `django.contrib.flatpages`, porque substitui o admin dele. No admin, o conteúdo das flatpages é editado com TinyMCE, configurado só para esse campo. A versão é o TinyMCE 5, que vem embutido no `django-tinymce` 3.7.1 do GeoNode e está sem suporte. Os módulos do app:
- `editor.py`: configuração, tags permitidas (`ALLOWED_TAGS`), sanitização (`sanitize_html`, com `bleach`) e armazenamento das imagens;
- `views.py`: upload;
- `admin.py`: formulário e admin;
- `signals.py`: exclusão das imagens;
- `templatetags/flatpages_editor.py`: filtro `sanitize_flatpage`;
- `templates/flatpages/default.html` e `static/flatpages_editor/js/image_upload.js`. Esse arquivo não pode ter nome terminado em `tinymce.js`: o TinyMCE localiza a própria pasta procurando um script com esse final e passaria a carregar temas e ícones da pasta errada.

O editor e o servidor seguem a mesma lista de tags:
- o editor só oferece tags de texto, link e imagem;
- o conteúdo é sanitizado ao salvar (`TinyMCEFlatpageForm`) e de novo ao exibir (filtro `sanitize_flatpage`).

A rota `pages/`, que publica as flatpages, e o sitemap continuam no `urls.py` do projeto.

O upload de imagens (`opengeosgb_flatpage_image_upload`, em `/opengeosgb/flatpages/upload-image`) aceita só usuários da equipe, exige o token CSRF (a função JS envia o token) e valida a imagem com o Pillow (PNG, JPEG, GIF ou WebP, até 5 MB). As imagens são gravadas por página, em `MEDIA_ROOT/flatpages/<id_da_página>/<nome>.<ext>`, e servidas em `/uploaded/flatpages/<id>/…`. O nome é o original normalizado com `slugify`; nomes repetidos recebem sufixo, e a extensão vem do formato validado. Numa página ainda não salva, o upload vai para `flatpages/tmp/<uuid>/`; ao salvar, `move_temp_images` (chamado no `save_model` do admin) move a imagem para a pasta da página e corrige o endereço no conteúdo. Nas páginas, `<img>` aceita `src` nessa pasta ou externo (`http`/`https`); `data:` e `javascript:` são removidos.

**Catálogo CSW (app `opengeosgb.catalogue`, rótulo `opengeosgb_catalogue`).** Sobrescreve o catálogo do GeoNode 5.0.x sem mexer no núcleo. Entra no `INSTALLED_APPS` pelo `local_settings.py`, que também define `CATALOGUE["default"]["ENGINE"]` (variável `CATALOGUE_ENGINE`, padrão `opengeosgb.catalogue.backends.pycsw_local`), `CATALOGUE_DEFAULT_FORMAT` (`ISO` ou `ISO19115-3_2018`) e `CATALOG_METADATA_TEMPLATE`. Os módulos:
- `constants.py`: nomes dos formatos, templates e perfis do pycsw; sem dependências, para poder ser importado nos settings;
- `formats.py`: tabela de formatos (a do núcleo mais o ISO 19115-3) e a regra de `csw_typename`/`csw_schema`. O perfil `iso19115p3` do pycsw só devolve o XML gravado quando `csw_typename == 'mdb:MD_Metadata'`;
- `config.py`: monta a configuração do pycsw a cada uso, com mescla profunda, os settings vencendo e o perfil `iso19115p3` incluído;
- `backends/pycsw_local.py`: backend que herda do `pycsw_local` do núcleo. O `create_record`, chamado pelo `catalogue_post_save` em todos os caminhos (inclusive `regenerate_xml`), grava `csw_typename`/`csw_schema`; o `signals.py` faz o mesmo no `pre_save`, o que cobre o editor de metadados;
- `backends/pycsw_repository.py`: repositório do pycsw (`repository.source`, trocado em `config.py`) que corrige o `GetDomain`. O do núcleo agrega sobre o queryset do django-polymorphic, que falha com agregações posicionais, e todo `GetDomain` voltava vazio. Os settings fixam `domainquerytype = "list"` (variável `PYCSW_DOMAINQUERYTYPE`): valores com contagem, em vez de só mínimo e máximo;
- `views.py` e `urls.py`: o endpoint `/catalogue/csw`. É uma cópia adaptada do `csw_global_dispatch` do núcleo, porque o do núcleo redireciona quando o `ENGINE` não é o dele. As cláusulas do filtro são combinadas só com `AND`, e o conjunto passa por `filters.csw_dataset_filter`: só datasets aprovados, publicados e com completude acima de `CSW_MIN_METADATA_COMPLETENESS`;
- `templates/opengeosgb_catalogue/full_metadata_iso19139.xml` (cópia do template do núcleo mais o bloco de escala) e `full_metadata_iso19115-3.xml`, válido contra o XSD `mdb` 2.0. Os contatos (`mdb:contact` e `mri:pointOfContact`) vêm de `_iso19115-3_responsibility.xml`. Sem contatos, o dono entra como `pointOfContact`, porque `mdb:contact` é obrigatório;
- `validation.py` e `schemas/`: validação do XML contra o XSD, com uma cópia local dos schemas, para não depender de rede. `python manage.py fetch_metadata_schemas` atualiza a cópia, que não deve ser editada à mão. `python manage.py validate_metadata_xml [--id N]` valida o XML gravado nos recursos de um ambiente.

**Ao atualizar o GeoNode, compare com o núcleo:** `get_record`, `search_records` e `_csw_local_dispatch` do backend (com `geonode/catalogue/backends/pycsw_local.py`), a view (com `geonode/catalogue/views.py`), o template 19139 (com `catalogue/full_metadata.xml`) `filters.with_metadata_completeness` (com `ResourceBase.metadata_completeness`) e `pycsw_repository.query_domain` (com `geonode/catalogue/backends/pycsw_plugin.py`). Depois de trocar o formato, rode `python manage.py regenerate_xml` para regravar todos os registros. Ao mudar o template 19115-3, rode os testes: `python manage.py test opengeosgb.catalogue` (precisa de PostGIS); um deles valida o XML gerado contra o XSD.

**Padrões de recursos novos.** Em `opengeosgb/signals.py`, um `pre_save` age só na criação de um recurso: se as informações complementares estiverem com o texto padrão do GeoNode ("No information provided"), deixa o campo vazio. Para os recursos existentes, o comando `python manage.py clear_default_supplemental_information [--dry-run]` esvazia esse texto padrão. Ele não regrava o XML de metadados, que só é atualizado quando o recurso for salvo de novo.

**Traduções.** O `django.po` do opengeosgb (`LOCALE_PATHS`, tem prioridade sobre os catálogos do GeoNode e do allauth) também traduz strings do GeoNode, do mapstore-client e do allauth sem tradução pt-BR upstream. As do allauth ficam numa seção própria, marcadas com `# allauth`. Não rode `makemessages --no-obsolete` neste app: ele apagaria essas entradas. Os JSON de tradução do MapStore em pt-BR ficam em `src/opengeosgb/static/mapstore/{gn,ms}-translations/`. Os textos padrão do componente de seleção do client (react-select: "Select...", "No results found", "Loading...", "Type to search") são fixos em inglês e aparecem nos filtros por facet do catálogo, que o client monta da API de facets sem placeholder; `templates/opengeosgb/snippets/select_i18n.html`, incluído no `head.html` do client, troca esses textos no DOM pela tradução do `django.po` (só o texto igual ao padrão; em inglês nada muda). Ver também `FILTROS_CATALOGO.md`. O seletor de idioma (`templates/geonode-mapstore-client/snippets/language_selector.html`, cópia do client 5.0.3) mostra bandeiras de `static/opengeosgb/img/flags/<código>.png` (ex.: `pt-br.png`); a tag `language_flag` (`templatetags/opengeosgb_tags.py`) só usa a bandeira se a imagem existir e senão mostra o código (filtro `language_code_label`, ex.: `es-ES`), porque com o storage de manifesto um `{% static %}` ausente derruba o menu. Para um idioma novo, basta o PNG 24x24 com o código do `LANGUAGES`. A página de erro `templates/500.html` é cópia da do GeoNode 5.0.3 com OpenGeoSGB e o rastreador do projeto; o texto do `blocktrans` tem de ser idêntico (quebras e espaços) ao msgid do `django.po`. O `urls.py` reexporta o `handler500` do GeoNode (`geonode.views.err500`, que renderiza o 500.html com a requisição); sem ele, vale o handler padrão do Django.

**Imagem Docker.** O `Dockerfile` parte de `geonode/geonode-base`, instala `src/requirements.txt` (que traz o GeoNode do branch `5.0.x`) e depois faz `pip install -e .` em `src/`. Ao mudar o branch do GeoNode, atualize `src/requirements.txt` e reconstrua a imagem.

## Problemas conhecidos (pendentes nas dependências)

- **[mapstore-client]** **Caixas "Publicado" e "Aprovado" não aparecem no painel de configurações do recurso (`DetailsSettings`).** Em `client/js/utils/ResourceUtils.js`, `RESOURCE_PUBLISHING_PROPERTIES` e `RESOURCE_OPTIONS_PROPERTIES` são constantes calculadas no carregamento do módulo (`filterResourcePublishingProperties()`). Elas leem `getConfigProp('geoNodeSettings').isPublishedOptionEnabled` e `isApprovedOptionEnabled` antes de o client carregar a configuração da página, então `is_published` e `is_approved` são sempre removidos, mesmo com `RESOURCE_PUBLISHING=True` e `ADMIN_MODERATE_UPLOADS=True` e com o usuário admin. O problema existe na 5.0.3 instalada e continua na `master` e no `5.0.x` upstream; não há issue aberta.
  - **Correção prevista:** trocar as constantes por funções avaliadas no uso, em `DetailsSettings.jsx`, `epics/gnsave.js` e `selectors/resource.js`. Não dá para contornar no opengeosgb, porque o cálculo acontece no carregamento do bundle. Até lá, aprovar e publicar pelo admin do Django ou pela API (`PATCH /api/v2/resources/<pk>`).
  - **Admin do Django:** `opengeosgb/admin.py` substitui os admins de Dataset, Map, Document e GeoApp (este último cobre dashboards e GeoStories). Ele acrescenta as ações em lote Aprovar, Publicar, Aprovar e publicar, Despublicar e Reprovar. Quando `is_approved` ou `is_published` mudam, seja pelas ações ou pela edição na lista ou no formulário, o recurso é salvo com `save(notify=True)`, com os campos `was_*` sincronizados com o banco. O save padrão do admin (`notify=False`) só gravaria os campos, sem atualizar as permissões do fluxo, as regras do GeoFence e as notificações. Com `ADMIN_MODERATE_UPLOADS` e `RESOURCE_PUBLISHING` ativos, aprovar e publicar concede `view` e `download` ao usuário anônimo.

## Pendências

Marcação de dependência: **[fork geonode]** depende do fork `nds-cprm/geonode`; **[mapstore-client]** depende do geonode-mapstore-client; **[opengeosgb]** resolve-se no próprio projeto (ou no submódulo `docker/`).

- **[opengeosgb]** **Revisar a política de cookies.** As flatpages `/pages/politica-de-cookies/` e `/pages/cookie-policy/` (versão em inglês) foram redigidas com base na página de LGPD do SGB e no Termo de Uso e Aviso de Privacidade do gov.br, e precisa da revisão do encarregado de dados (dpo@sgb.gov.br) ou da área jurídica. Se o container do Google Tag Manager ativar outras ferramentas além do Google Analytics, a seção 2.2 da página e a limpeza de cookies ao recusar (regex em `cookie_consent.html`) precisam ser atualizadas.
- **[fork geonode]** **Formato do download Excel.** O link "Excel" gerado pelo GeoNode usa `excel` (.xls, limite de 65.536 linhas). O ideal seria `excel2007` (.xlsx). O link é criado em `geonode/geoserver/ows.py`, no fork.
- **[opengeosgb]** **Fixture de licença do opengeosgb.** Em `src/fixtures/opengeosgb/opengeosgb-license.json`, a licença Creative Commons 4.0 (BY-NC) está com `identifier` vazio. O editor localiza licenças por esse campo, então ela não pode ser usada até receber um identificador (ex.: `cc-by-nc-4.0`).
- **[mapstore-client]** **Coluna "Descrição" da lista do catálogo.** No `static/mapstore/configs/localConfig.json` do client, a coluna da visualização em lista (`ResourcesGrid`, `cfg.metadata.list`) lê o campo `description`, que não existe na API de recursos do GeoNode; a descrição vem em `abstract` (HTML) e `raw_abstract` (texto puro). **Contorno no opengeosgb:** `templates/geonode-mapstore-client/_geonode_config.html` (`overrideLocalConfig`) troca `description` por `raw_abstract` em tempo de execução. A correção definitiva é trocar o campo no `localConfig.json` do client; quando isso acontecer, o contorno pode ser removido.
- **[mapstore-client]** **Data no cabeçalho do painel de propriedades.** A linha "Recurso do tipo dataset de admin / data" vem de `client/js/plugins/ResourceDetails/containers/DetailsPanel.jsx` (l. 147). O formato da data está fixo no código, `moment(resource.date).format('MMMM Do YYYY')`, e não é configurável; o `overrideLocalConfig` não alcança esse trecho. Correção: usar `'L'` (data numérica do idioma), como no resto do projeto. As palavras "a"/"from" da mesma linha (`gnviewer.resourceOrigin.*`) já foram traduzidas em `static/mapstore/gn-translations/data.pt-BR.json` do opengeosgb, que sobrescreve o arquivo do client.
- **[mapstore-client]** **Tipo de recurso sem tradução no cabeçalho do painel de propriedades.** No mesmo trecho de `DetailsPanel.jsx` (l. 134-136), o tipo ("dataset", "map", "document"...) é impresso direto (`{resource.resource_type}`), sem passar por `<Message>`, então não adianta traduzir. Correção, nos dois ramos (com e sem link): `<Message msgId={`gnviewer.${resource.resource_type}`} />`. As chaves `gnviewer.dataset`/`map`/`document`/`geostory`/`dashboard` já existem e estão traduzidas em minúsculas ("conjunto de dados", "mapa", "documento"...). O link do filtro (`?f=<tipo>`) continua com o valor cru.
- **[mapstore-client]** **Contador de visualizações.** O `popular_count` só é incrementado pela rota legada de dataset embutido, por isso foi retirado da página de metadados. Uma contagem real depende do mapstore-client registrar o acesso à página do recurso.
- **[opengeosgb]** **Publicar as mudanças do GeoServer.** As extensões `excel` e `geopkg-output` foram adicionadas ao Dockerfile do submódulo `docker/` (`nds-cprm/geonode-docker`, branch `opengeosgb`). Falta fazer commit e push no submódulo, atualizar a referência no opengeosgb e reconstruir a imagem nos outros ambientes.
- **[opengeosgb]** **Imagens órfãs das flatpages.** Dois casos deixam arquivos sem uso em `MEDIA_ROOT/flatpages/`:
  - imagens enviadas numa página nova que acabou não sendo salva ficam em `flatpages/tmp/<uuid>/`;
  - imagens removidas do conteúdo de uma página continuam em `flatpages/<id>/`.

  Uma solução seria um comando de limpeza, por exemplo agendado no Celery beat, que apague as pastas de `tmp/` com mais de um dia e os arquivos de `flatpages/<id>/` que não aparecem no conteúdo da página. Quando a página é apagada, a pasta dela já é removida (sinal `post_delete`).
- **[opengeosgb]** **Limpar o texto padrão antigo.** Rodar `clear_default_supplemental_information` (primeiro com `--dry-run`) nos ambientes com recursos que ainda têm "No information provided".

## Cuidados

- `secrets/`, `draft/` (backups `.backup` de produção) e os `.env.*` contêm credenciais e dados reais. Não leia, não copie para outros lugares e não versione.
