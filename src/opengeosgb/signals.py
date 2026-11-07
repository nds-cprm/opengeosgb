from geonode.base.models import ResourceBase

# Texto padrão do GeoNode para "informações complementares"; no opengeosgb o campo fica vazio
GEONODE_DEFAULT_SUPPLEMENTAL_INFORMATION = "No information provided"


def set_resource_defaults(sender, instance, **kwargs):
    """
    Aplica os padrões do opengeosgb só na criação de recursos: informações complementares
    vazias no lugar do texto padrão do GeoNode.
    """
    if not isinstance(instance, ResourceBase) or not instance._state.adding:
        return

    geonode_defaults = {
        GEONODE_DEFAULT_SUPPLEMENTAL_INFORMATION,
        str(ResourceBase._meta.get_field("supplemental_information").default),
    }
    if str(instance.supplemental_information) in geonode_defaults:
        instance.supplemental_information = ""
