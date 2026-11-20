from functools import lru_cache

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.translation import to_locale

register = template.Library()

FLAG_PATH = "opengeosgb/img/flags/{}.png"


@lru_cache(maxsize=None)
def _flag_url(language_code):
    path = FLAG_PATH.format(language_code)
    # só monta a URL se a imagem existir: com o storage de manifesto (DEBUG=False e
    # CACHE_BUSTING_STATIC_ENABLED), {% static %} de um arquivo ausente levanta erro e quebraria o menu
    return static(path) if finders.find(path) else ""


@register.simple_tag
def language_flag(language_code):
    """URL da bandeira do idioma (static/opengeosgb/img/flags/<código>.png), ou "" se não houver imagem."""
    return _flag_url(str(language_code or "").lower())


@register.filter
def language_code_label(language_code):
    """Código do idioma no formato de exibição: "es-es" -> "es-ES", "pt-br" -> "pt-BR" (usado sem bandeira)."""
    return to_locale(str(language_code or "")).replace("_", "-")
