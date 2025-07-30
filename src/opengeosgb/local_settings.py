from geonode.settings import *

# Flatpages
if SITE_ID and ("django.contrib.flatpages" not in INSTALLED_APPS):
    if "django.contrib.sites" not in INSTALLED_APPS:
        INSTALLED_APPS += ("django.contrib.sites")

    INSTALLED_APPS += ("django.contrib.flatpages",)
    MIDDLEWARE += ("django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",)
    

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