from geonode.settings import *

# Flatpages
if SITE_ID and ("django.contrib.flatpages" not in INSTALLED_APPS):
    if "django.contrib.sites" not in INSTALLED_APPS:
        INSTALLED_APPS += ("django.contrib.sites",)

    INSTALLED_APPS += ("django.contrib.flatpages",)
    MIDDLEWARE += ("django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",)

# Editor de flatpages (TinyMCE, sanitização, imagens por página); precisa vir depois de
# django.contrib.flatpages, pois substitui o admin dele
if "django.contrib.flatpages" in INSTALLED_APPS:
    INSTALLED_APPS += ("opengeosgb.flatpages_editor.apps.FlatpagesEditorConfig",)
    

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

# CATALOGUE_METADATA_TEMPLATE = "catalogue/full_metadata.xml"
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


# Google Tag Manager
GOOGLE_TAG_MANAGER_ID = os.getenv("GOOGLE_TAG_MANAGER_ID", "") 
TEMPLATES[0]["OPTIONS"]["context_processors"].append("opengeosgb.context_processors.google_tag_manager_snippet")
