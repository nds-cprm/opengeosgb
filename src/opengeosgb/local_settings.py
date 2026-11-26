from geonode.settings import *
# constantes sem dependências, importáveis num módulo de settings
from geonode_catalogue_iso19115_3.constants import ENGINE as CATALOGUE_ISO19115_3_ENGINE, ISO19115_3, ISO19139

# Flatpages
if SITE_ID and ("django.contrib.flatpages" not in INSTALLED_APPS):
    if "django.contrib.sites" not in INSTALLED_APPS:
        INSTALLED_APPS += ("django.contrib.sites",)

    INSTALLED_APPS += ("django.contrib.flatpages",)
    MIDDLEWARE += ("django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",)

# Editor de flatpages (pacote geonode-flatpages-editor: TinyMCE, sanitização, imagens por página);
# precisa vir depois de django.contrib.flatpages, pois substitui o admin dele
if "django.contrib.flatpages" in INSTALLED_APPS:
    INSTALLED_APPS += ("geonode_flatpages_editor",)

    # Limpeza diária (3h) das imagens órfãs das flatpages. A tarefa não define fila, e o worker do
    # GeoNode só consome as filas de CELERY_TASK_QUEUES, por isso a fila "cleanup"
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE["flatpages-cleanup-images"] = {
        "task": "geonode_flatpages_editor.cleanup_orphan_images",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "cleanup"},
    }

# Proxy reverso: o nginx sempre sobrescreve X-Forwarded-Proto com o esquema público (HTTP_SCHEME,
# ou PUBLIC_SCHEME atrás de um load balancer que termina TLS) e o Origin com a URL pública. Sem
# isto, o Django vê "http" e recusa os POSTs com "Origin checking failed" quando o público é https.
# Seguro enquanto a porta do Django não estiver acessível de fora sem passar pelo nginx.
EXTERNAL_PROXY_ENABLED = ast.literal_eval(os.getenv("EXTERNAL_PROXY_ENABLED", "False"))
if EXTERNAL_PROXY_ENABLED:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Internationalization
# geonode.settings lines 1551-1565
LANGUAGES = ast.literal_eval(os.getenv("LANGUAGES", MAPSTORE_DEFAULT_LANGUAGES))

# Recaptcha
# RECAPTCHA_ENABLED = ast.literal_eval(os.environ.get("RECAPTCHA_ENABLED", "False"))

if RECAPTCHA_ENABLED:
    ACCOUNT_FORMS = {
        'login': 'opengeosgb.account.forms.GovBRReCaptchaLoginForm',
        'signup': 'opengeosgb.account.forms.GovBRReCaptchaSignupForm'
    }
else:
    ACCOUNT_FORMS = {
        'login': 'opengeosgb.account.forms.GovBRLoginForm',
        'signup': 'opengeosgb.account.forms.GovBRSignupForm'
    }

# Social Accounts
INSTALLED_APPS += (
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.orcid',
    'allauth.socialaccount.providers.openid_connect',
)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'FETCH_USERINFO' : True
    },
    'orcid': {
        # Base domain of the API. Default value: 'orcid.org', for the production API
        'BASE_DOMAIN':'sandbox.orcid.org',  # for the sandbox API
        # Member API or Public API? Default: False (for the public API)
        'MEMBER_API': True,  # for the member API
    },
    'openid_connect': {
        # "SCOPE": [
        #     "openid",
        #     "email",
        #     "phone",
        #     "profile",
        #     # "govbr_empresa",
        #     # "govbr_confiabilidades"
        # ],
        "OAUTH_PKCE_ENABLED": True,
    },
}

SOCIALACCOUNT_PROFILE_EXTRACTORS = {
    "govbr": "opengeosgb.account.profileextractors.GovBRExtractor"
}

# # Haystack Search
# HAYSTACK_SEARCH = ast.literal_eval(os.getenv("HAYSTACK_SEARCH", "False"))

# if HAYSTACK_SEARCH:    
#     INSTALLED_APPS += (
#         'haystack',
#     )

#     HAYSTACK_CONNECTIONS = {
#     'default': {
#         'ENGINE': 'haystack.backends.elasticsearch7_backend.Elasticsearch7SearchEngine',
#         'URL': os.getenv("HAYSTACK_ENGINE_URL"),
#         'INDEX_NAME': os.getenv("HAYSTACK_ENGINE_INDEX_NAME"),
#     },
# }

# PyCSW Custom
PYCSW["CONFIGURATION"]["metadata"]["inspire"]["enabled"] = False

PYCSW["CONFIGURATION"]["metadata"]["identification"] = {
    "title": "OpenGeoSGB - Serviços de catálogo",
    "description": "Catálogo de dados e serviços do Serviço Geológico do Brasil",
    "keywords": ["sdi", "catalogue", "discovery", "metadata"],
    "keywords_type": "theme",
    "fees": "None",
    "accessconstraints": "None",
}

PYCSW["CONFIGURATION"]["metadata"]["provider"] = {
    "name": "Serviço Geológico do Brasil",
    "url": "https://www.sgb.gov.br",
}

PYCSW["CONFIGURATION"]["metadata"]["contact"] = {
    "name": "Carlos Eduardo Miranda Mota",
    "position": "Pesquisador em Geociências",
    "address": "Av. Pasteur, 404, Urca",
    "city": "Rio de Janeiro",
    "stateorprovince": "RJ",
    "postalcode": "22240-140",
    "country": "Brasil",
    "phone": "+55 21 2546-0320",
    "fax": "",
    "email": "carlos.mota@sgb.gov.br",
    "url": "",
    "hours": "8:00 - 18:00",
    "instructions": "Apenas em horas de serviço. Indisponível nos fins de semana.",
    "role": "pointOfContact",
}

# Catálogo CSW com ISO 19115-3 (app geonode-catalogue-iso19115-3). O backend do app grava o
# metadata_xml no formato de CATALOGUE_DEFAULT_FORMAT (ISO19115-3_2018 ou ISO, isto é, ISO 19139);
# a view /catalogue/csw do app é inserida antes da do GeoNode em urls.py
INSTALLED_APPS += ("geonode_catalogue_iso19115_3",)

CATALOGUE["default"]["ENGINE"] = os.getenv("CATALOGUE_ENGINE", CATALOGUE_ISO19115_3_ENGINE)
CATALOGUE_DEFAULT_FORMAT = os.getenv("CATALOGUE_DEFAULT_FORMAT", ISO19115_3)

# Templates do opengeosgb: estendem os do app e acrescentam a escala (campo esparso "scale")
CATALOG_METADATA_TEMPLATE = os.getenv(
    "CATALOG_METADATA_TEMPLATE",
    {
        ISO19115_3: "opengeosgb/catalogue/full_metadata_iso19115-3.xml",
        ISO19139: "opengeosgb/catalogue/full_metadata_iso19139.xml",
    }.get(CATALOGUE_DEFAULT_FORMAT, ""),
)
# o aviso W002 aponta template diferente do padrão do formato; os do opengeosgb o estendem
SILENCED_SYSTEM_CHECKS = list(globals().get("SILENCED_SYSTEM_CHECKS", [])) + ["geonode_catalogue_iso19115_3.W002"]

# GetDomain devolve todos os valores com a contagem, e não só mínimo e máximo
PYCSW["CONFIGURATION"]["server"]["domainquerytype"] = "list"

# O CSW só entrega datasets e mapas aprovados e publicados, para todos os usuários (inclusive
# admin). PYCSW["FILTER"] é do GeoNode, que o aplica só no GetRecords (padrão: só datasets); a
# view /catalogue/csw do app geonode_catalogue_iso19115_3 o aplica também no GetRecordById e
# no GetDomain. Ele substitui o padrão inteiro
PYCSW["FILTER"] = {
    "resource_type__in": ["dataset", "map"],
    "is_approved": True,
    "is_published": True,
}

# CATALOGUE_METADATA_XSL = "/static/metadataxsl/metadata.xsl"

# DOWNLOAD_FORMATS_METADATA = [
#     # 'Atom', 'DIF', 
#     'Dublin Core', #'ebRIM', 
#     'FGDC', 'ISO',
# ]

# DOWNLOAD_FORMATS_VECTOR = [
#     'JPEG', 'PDF', 'PNG', 'Zipped Shapefile', 
#     #'GML 2.0', 'GML 3.1.1', 
#     # 'CSV',
#     'Excel', 'GeoJSON', 'KML', 'View in Google Earth', 'Tiles',
# ]

# DOWNLOAD_FORMATS_RASTER = [
#     'JPEG', 'PDF', 'PNG' 'Tiles',
# ]

# https://docs.geonode.org/en/master/basic/settings/index.html#ui-required-fields


# Facet de escala (campo esparso "scale") para a barra de filtros do catálogo
FACET_PROVIDERS = list(FACET_PROVIDERS) + [
    {"class": "opengeosgb.metadata.facets.ScaleFacetProvider", "config": {"order": 8, "type": "select"}},
]

# Traduções do client (MapStore): além das do client, as do opengeosgb (textos próprios, como
# o rótulo "Escala" do painel de propriedades), em static/opengeosgb/translations/data.<locale>.json
_translations_path = MAPSTORE_TRANSLATIONS_PATH
if isinstance(_translations_path, str):  # pode vir como texto da variável de ambiente
    _translations_path = ast.literal_eval(_translations_path) if _translations_path.startswith("[") else [_translations_path]
MAPSTORE_TRANSLATIONS_PATH = list(_translations_path) + ["/static/opengeosgb/translations"]

# Google Tag Manager
GOOGLE_TAG_MANAGER_ID = os.getenv("GOOGLE_TAG_MANAGER_ID", "") 
TEMPLATES[0]["OPTIONS"]["context_processors"].append("opengeosgb.context_processors.google_tag_manager_snippet")

# Páginas institucionais (flatpages) por idioma, usadas no aviso de cookies
# (opengeosgb/snippets/cookie_consent.html, que carrega o Google Tag Manager só depois do aceite)
# e no rodapé (geonode-mapstore-client/snippets/footer.html)
COOKIE_POLICY_URL = os.getenv("COOKIE_POLICY_URL", "/pages/politica-de-cookies/")
# versão da política por idioma da interface (flatpages separadas)
COOKIE_POLICY_URLS = {
    "pt": COOKIE_POLICY_URL,
    "en": os.getenv("COOKIE_POLICY_URL_EN", "/pages/cookie-policy/"),
}

# Página "Sobre" (flatpage) por idioma, usada no rodapé
ABOUT_PAGE_URL = os.getenv("ABOUT_PAGE_URL", "/pages/sobre/")
ABOUT_PAGE_URLS = {
    "pt": ABOUT_PAGE_URL,
    "en": os.getenv("ABOUT_PAGE_URL_EN", "/pages/about/"),
}
TEMPLATES[0]["OPTIONS"]["context_processors"].append("opengeosgb.context_processors.site_pages")
