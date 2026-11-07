import json
import re

from geonode.metadata.models import SparseField

from .fields import COMMON_SCALES, SCALE_FIELD


def parse_scale(text: str):
    """
    Denominador a partir do texto digitado: aceita "250000", "250.000", "250,000" e "1:250.000".
    Retorna None se o texto não for uma escala válida.
    """
    text = (text or "").strip()
    text = re.sub(r"^1\s*:\s*", "", text)
    digits = re.sub(r"[\s.,]", "", text)
    if not digits.isdigit():
        return None
    value = int(digits)
    return value if value >= 1 else None


def scale_label(denominator: int) -> str:
    """Rótulo da escala no formato brasileiro, ex.: 1:250.000."""
    return f"1:{denominator:,}".replace(",", ".")


def scale_option(denominator: int) -> dict:
    return {"id": denominator, "label": scale_label(denominator)}


def used_scales() -> set:
    """Denominadores já gravados em recursos."""
    used = set()
    for value in SparseField.objects.filter(name=SCALE_FIELD).values_list("value", flat=True):
        try:
            data = json.loads(value) if value else None
        except ValueError:
            continue
        denominator = data.get("id") if isinstance(data, dict) else data
        if isinstance(denominator, int) and denominator >= 1:
            used.add(denominator)
    return used


def scale_suggestions(q: str = None) -> list:
    """
    Opções do autocomplete: escalas comuns e já usadas que casam com o texto digitado.
    Se o texto for uma escala válida fora da lista, ela vem primeiro, permitindo valores livres
    (o editor do GeoNode não aceita valores digitados em seleção única).
    """
    candidates = sorted(set(COMMON_SCALES) | used_scales())
    typed = parse_scale(q) if q else None
    if not q:
        return [scale_option(d) for d in candidates]

    digits = re.sub(r"[^\d]", "", re.sub(r"^\s*1\s*:\s*", "", q))
    options = [scale_option(d) for d in candidates if digits and digits in str(d)]
    if typed and typed not in candidates:
        options.insert(0, scale_option(typed))
    return options
