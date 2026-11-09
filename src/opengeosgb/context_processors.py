import re

from django.conf import settings

GTM_REGEX = re.compile(r'^GTM-[A-Z0-9]{4,10}$')


def google_tag_manager_snippet(request):
    gtag = str(getattr(settings, "GOOGLE_TAG_MANAGER_ID", "") or "")

    return {
        "GOOGLE_TAG_MANAGER_ID": gtag if GTM_REGEX.match(gtag) else ""
    }


def _localized_url(request, urls_setting, default_setting):
    """Endereço no idioma da requisição: o dicionário urls_setting mapeia o idioma ("pt", "en")
    para o endereço; sem correspondência, usa default_setting."""
    language = (getattr(request, "LANGUAGE_CODE", "") or "").split("-")[0]
    urls = getattr(settings, urls_setting, {}) or {}
    return urls.get(language) or getattr(settings, default_setting, "")


def site_pages(request):
    """
    Endereços das páginas institucionais (flatpages) no idioma da requisição, usados no aviso de
    cookies (opengeosgb/snippets/cookie_consent.html) e no rodapé (snippets/footer.html).
    """
    return {
        "COOKIE_POLICY_URL": _localized_url(request, "COOKIE_POLICY_URLS", "COOKIE_POLICY_URL"),
        "ABOUT_PAGE_URL": _localized_url(request, "ABOUT_PAGE_URLS", "ABOUT_PAGE_URL"),
    }


def map_constraints(request):
    """
    Limite do canvas dos mapas (MAP_RESTRICTED_EXTENT, em local_settings.py), aplicado ao
    localConfig do client em templates/geonode-mapstore-client/_geonode_config.html.
    """
    return {
        "MAP_RESTRICTED_EXTENT": getattr(settings, "MAP_RESTRICTED_EXTENT", None),
        "MAP_RESTRICTED_EXTENT_CRS": getattr(settings, "MAP_RESTRICTED_EXTENT_CRS", "EPSG:4326"),
    }
