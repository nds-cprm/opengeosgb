from django.shortcuts import redirect, get_object_or_404
from geonode.base.models import ResourceBase


def legacy_metadata_detail(request, layername):
    """
    Converte chamadas de metadados do geonode 4 para o 5
    https://opendatah.sgb.gov.br/datasets/p3m:vw_cprm_map_geo_25k/metadata_detail
    re_path(r"^(?P<layername>[^/]*)/metadata_detail$", views.dataset_metadata_detail, name="dataset_metadata_detail"),

    https://opendata.sgb.gov.br/metadata/676
    re_path(r"^metadata/(?P<pk>[^/]*)$", views.metadata, name='metadata'),
    """
    pk = get_object_or_404(ResourceBase, alternate=layername).pk   # colcoar um index em alternate

    # Redireciona para a nova rota passando o 'pk' obtido a partir de layername
    return redirect('metadata', pk=pk, permanent=True)
