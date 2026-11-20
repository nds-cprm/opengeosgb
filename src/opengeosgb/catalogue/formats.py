"""
Formatos de metadados do catálogo.

O GeoNode 5.0.x só conhece o ISO 19139 (``gmd``). Aqui a tabela do núcleo é
estendida com o ISO 19115-3, e o formato gravado em ``metadata_xml`` passa a
vir de ``settings.CATALOGUE_DEFAULT_FORMAT``.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from lxml import etree

from geonode.catalogue.backends.generic import METADATA_FORMATS as CORE_METADATA_FORMATS

from .constants import ISO19115_3, ISO19139, METADATA_TEMPLATES, PYCSW_PROFILES  # noqa: F401

# nome do formato -> (typename, namespace/outputschema)
METADATA_FORMATS = {
    **CORE_METADATA_FORMATS,
    ISO19115_3: ("mdb:MD_Metadata", "http://standards.iso.org/iso/19115/-3/mdb/2.0"),
}


def default_format():
    fmt = getattr(settings, "CATALOGUE_DEFAULT_FORMAT", ISO19115_3)
    if fmt not in METADATA_TEMPLATES:
        raise ImproperlyConfigured(
            f"CATALOGUE_DEFAULT_FORMAT inválido: {fmt!r}. Use um de {', '.join(METADATA_TEMPLATES)}."
        )
    return fmt


def default_typename():
    return METADATA_FORMATS[default_format()][0]


def default_schema():
    return METADATA_FORMATS[default_format()][1]


def md_metadata_class(fmt=None):
    """Classe do owslib que lê o formato (``owslib.iso`` ou ``owslib.iso3``)."""
    if (fmt or default_format()) == ISO19115_3:
        from owslib.iso3 import MD_Metadata
    else:
        from owslib.iso import MD_Metadata
    return MD_Metadata


def format_of_xml(xml):
    """Nome do formato a partir do elemento raiz de um XML, ou ``None``."""
    if not xml:
        return None
    try:
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    except (etree.XMLSyntaxError, ValueError):
        return None
    namespace = etree.QName(root).namespace
    for name, (_typename, schema) in METADATA_FORMATS.items():
        if schema == namespace and name in METADATA_TEMPLATES:
            return name
    return None


def csw_format_fields(instance):
    """
    Valores de ``csw_typename`` e ``csw_schema`` para o XML que o recurso guarda.

    O perfil ``iso19115p3`` do pycsw só devolve o XML gravado quando
    ``csw_typename == 'mdb:MD_Metadata'`` (e o ``apiso`` só quando é
    ``gmd:MD_Metadata``); por isso esses campos precisam acompanhar o formato.
    XML enviado pelo usuário e preservado mantém o formato dele.
    """
    fmt = None
    if getattr(instance, "metadata_uploaded", False) and getattr(instance, "metadata_uploaded_preserve", False):
        fmt = format_of_xml(getattr(instance, "metadata_xml", None))
    typename, schema = METADATA_FORMATS[fmt or default_format()]
    return {"csw_typename": typename, "csw_schema": schema}
