from django.db.models import Q
from django.http import JsonResponse

from geonode.base.models import Region
from geonode.metadata.api.views import MetadataRegionsAutocomplete

from .i18n import REGION_MAX_TRANSLATED_LEVEL, normalize_text, region_label
from .scales import scale_suggestions


def scales_autocomplete(request):
    """Autocomplete do campo de escala do editor de metadados."""
    return JsonResponse({"results": scale_suggestions(request.GET.get("q"))})


class RegionsI18nAutocomplete(MetadataRegionsAutocomplete):
    """
    Autocomplete de regiões do editor de metadados com nomes traduzidos.

    A busca casa com o nome original (banco) e com o nome traduzido, sem diferenciar
    acentos; a comparação com a tradução só percorre as regiões traduzíveis.
    """

    def get_queryset(self):
        qs = Region.objects.order_by("pk")
        if self.q:
            term = normalize_text(self.q)
            translated_ids = [
                region.id
                for region in Region.objects.filter(level__lte=REGION_MAX_TRANSLATED_LEVEL).only("id", "name", "level")
                if term in normalize_text(region_label(region))
            ]
            qs = qs.filter(Q(name__icontains=self.q) | Q(id__in=translated_ids))
        return qs

    def get_result_label(self, result):
        return region_label(result)
