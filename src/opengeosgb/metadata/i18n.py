import unicodedata

from django.utils.translation import pgettext

# Contexto (msgctxt) dos nomes de regiões no django.po do opengeosgb
REGION_MSGCTXT = "metadata region"

# Só regiões até este nível (global, continentes, sub-regiões e países) são traduzidas;
# estados (4) e municípios (5) brasileiros já estão em português e não entram no .po
REGION_MAX_TRANSLATED_LEVEL = 3


def normalize_text(text: str) -> str:
    """Texto sem acentos e em minúsculas, para ordenação e busca."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def region_label(region) -> str:
    """Nome da região no idioma ativo."""
    if region.level <= REGION_MAX_TRANSLATED_LEVEL:
        return pgettext(REGION_MSGCTXT, region.name)
    return region.name
