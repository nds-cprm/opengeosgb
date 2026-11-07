"""
Filtro por escala no catálogo (barra de filtros do client).

- ScaleFacetProvider: facet "scale" da API /api/v2/facets, com as escalas usadas e a contagem de
  recursos de cada uma. Registrado em FACET_PROVIDERS (local_settings.py).
- ScaleFilter: filtro da API de recursos para o parâmetro "scale=<denominador>" (pode repetir),
  enviado pelo client ao escolher uma escala. Acrescentado ao ResourceBaseViewSet no ready() do app;
  a API de facets usa o mesmo filtro para as contagens.

A escala é um campo esparso (SparseField "scale", valor JSON {"id": denominador, "label": "1:250.000"}),
por isso não é filtrável pelo filtro padrão do dynamic_rest (filter{...}).
"""
import logging

from django.db.models import Count, JSONField
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _
from rest_framework.filters import BaseFilterBackend

from geonode.facets.models import DEFAULT_FACET_PAGE_SIZE, FacetProvider
from geonode.metadata.models import SparseField

from .fields import SCALE_FIELD
from .scales import scale_label

logger = logging.getLogger(__name__)

FACET_TYPE_SCALE = "scale"
SCALE_QUERY_PARAM = "scale"


def scale_entries():
    """Registros de escala com o denominador extraído do JSON (campo "denominator")."""
    return (
        SparseField.objects.filter(name=SCALE_FIELD)
        .annotate(data=Cast("value", output_field=JSONField()))
        .annotate(denominator=KeyTextTransform("id", "data"))
        .exclude(denominator__isnull=True)
    )


class ScaleFilter(BaseFilterBackend):
    """Filtra recursos pela escala: ?scale=250000&scale=1000000."""

    def filter_queryset(self, request, queryset, view):
        values = [value for value in request.query_params.getlist(SCALE_QUERY_PARAM) if value.isdigit()]
        if not values:
            return queryset
        return queryset.filter(pk__in=scale_entries().filter(denominator__in=values).values("resource_id"))


class ScaleFacetProvider(FacetProvider):
    """Facet das escalas usadas nos recursos visíveis."""

    @property
    def name(self) -> str:
        return SCALE_FIELD

    def get_info(self, lang="en", **kwargs) -> dict:
        return {
            "name": self.name,
            "filter": SCALE_QUERY_PARAM,
            "label": _("Scale"),
            "type": FACET_TYPE_SCALE,
        }

    def get_facet_items(
        self,
        queryset,
        start: int = 0,
        end: int = DEFAULT_FACET_PAGE_SIZE,
        lang="en",
        topic_contains: str = None,
        keys: set = {},
        **kwargs,
    ) -> (int, list):
        q = scale_entries().filter(resource__in=queryset)
        if keys:
            q = q.filter(denominator__in=[str(key) for key in keys])
        rows = q.values("denominator").annotate(count=Count("resource", distinct=True))

        topics = [
            {"key": row["denominator"], "label": scale_label(int(row["denominator"])), "count": row["count"]}
            for row in rows
            if str(row["denominator"]).isdigit()
        ]
        if topic_contains:
            digits = "".join(ch for ch in topic_contains if ch.isdigit())
            topics = [t for t in topics if digits and digits in t["key"]]
        # da escala maior (denominador menor) para a menor
        topics.sort(key=lambda topic: int(topic["key"]))
        return len(topics), topics[start:end]

    def get_topics(self, keys: list, lang="en", **kwargs) -> list:
        return [{"key": str(key), "label": scale_label(int(key))} for key in keys if str(key).isdigit()]

    @classmethod
    def register(cls, registry, **kwargs) -> None:
        registry.register_facet_provider(ScaleFacetProvider(**kwargs))
