from geonode.base.models import ResourceBase

from .formats import csw_format_fields


def sync_csw_format(sender, instance, raw=False, **kwargs):
    """
    Mantém ``csw_typename`` e ``csw_schema`` de acordo com o formato do catálogo
    em todo ``save()`` de recurso.

    Cobre o editor de metadados, que salva o recurso e chama
    ``update_csw_metadata`` sem passar pelo ``catalogue_post_save``. Os demais
    caminhos passam pelo ``CatalogueBackend.create_record``. Um ``save`` com
    ``update_fields`` sem esses campos não os grava, mas o ``create_record``
    corrige no próximo ``catalogue_post_save``.
    """
    if raw or not isinstance(instance, ResourceBase):
        return
    for name, value in csw_format_fields(instance).items():
        setattr(instance, name, value)
