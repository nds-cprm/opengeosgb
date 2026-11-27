# Customizações do projeto

- **Settings:** toda customização vai em `src/opengeosgb/local_settings.py`, que importa `geonode.settings`. `settings.py` só contém o que é estrutural do template.
- **Templates e estáticos:** arquivos em `src/opengeosgb/templates/` e `src/opengeosgb/static/` sobrescrevem os do GeoNode e do mapstore-client quando têm o mesmo caminho relativo.
- **Escala:** os recursos ganham o campo "Escala" no painel de informações e um filtro "Escala" no catálogo (`src/opengeosgb/metadata/`).
- **Autenticação:** login com Google, ORCID e gov.br (OpenID Connect), formulários próprios e reCAPTCHA opcional (`RECAPTCHA_ENABLED`).
- **Páginas institucionais:** flatpages em `/pages/`, editadas no admin com um editor TinyMCE restrito; o HTML é sanitizado ao salvar e ao exibir. Cada idioma é uma página separada (`/pages/sobre/` e `/pages/about/`).
- **LGPD:** faixa de consentimento de cookies; o Google Tag Manager (`GOOGLE_TAG_MANAGER_ID`) só é carregado depois do aceite. Os endereços da política de cookies e da página "Sobre" são configuráveis (`COOKIE_POLICY_URL`, `COOKIE_POLICY_URL_EN`).
- **Links legados:** `datasets/<alternate>/metadata_detail`, do GeoNode 4, redireciona para `metadata/<pk>`.
- **Celery:** o `src/celery-cmd` sobe o beat, o worker comum e o worker de harvesting. Cada worker tem o próprio limite de memória por processo filho, em KB: `CELERY__MAX_MEMORY_PER_CHILD` (padrão 200000) para o comum e `CELERY__HARVESTER_MAX_MEMORY_PER_CHILD` (padrão 500000) para o de harvesting. No template do `geonode-project` (`5.0.x`), o limite do harvester lê a variável do worker comum e fica em 200000. Aqui ele foi corrigido, então o harvester não segue mais o `CELERY__MAX_MEMORY_PER_CHILD`. Para manter o limite antigo num ambiente, defina `CELERY__HARVESTER_MAX_MEMORY_PER_CHILD` no `.env`.
