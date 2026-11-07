from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import get_language_from_request
from django.utils.translation import gettext as _

from geonode.base.models import Region, ResourceBase
from geonode.metadata.api.views import MetadataRegionsAutocomplete
from geonode.utils import resolve_object

from .i18n import REGION_MAX_TRANSLATED_LEVEL, normalize_text, region_label
from .page import build_metadata_page
from .scales import scale_suggestions


def metadata_page(request, pk, template="geonode-mapstore-client/metadata.html"):
    """
    Página de visualização de metadados. Substitui a view do geonode-mapstore-client
    (mesmas rotas e templates), verificando a permissão de leitura do recurso.
    """
    resource = resolve_object(
        request,
        ResourceBase,
        {"pk": pk},
        permission="base.view_resourcebase",
        permission_msg=_("You are not permitted to view this resource"),
    ).get_real_instance()
    lang = get_language_from_request(request)[:2]
    context = {"resource": resource, "metadata_groups": {}, "page": build_metadata_page(resource, lang, request.user)}
    return render(request, template, context=context)


def metadata_page_embed(request, pk):
    return metadata_page(request, pk, template="geonode-mapstore-client/metadata_embed.html")


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
