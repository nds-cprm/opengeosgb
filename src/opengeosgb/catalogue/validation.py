"""
Validação do XML de metadados contra o XSD do formato.

Os schemas ficam em ``schemas/`` (cópia local gerada por
``python manage.py fetch_metadata_schemas``), então a validação não usa rede.
Carregar o schema leva alguns segundos; ele é carregado uma vez por processo.
"""

import functools
import pathlib
import urllib.parse

from lxml import etree

from .constants import ISO19115_3

SCHEMAS_DIR = pathlib.Path(__file__).resolve().parent / "schemas"

# formato -> URL do schema raiz
SCHEMA_ROOTS = {
    ISO19115_3: "https://schemas.isotc211.org/19115/-3/mdb/2.0/mdb.xsd",
}


class SchemaNotAvailable(Exception):
    pass


def _schema_path(fmt):
    url = SCHEMA_ROOTS.get(fmt)
    if url is None:
        raise SchemaNotAvailable(f"Não há XSD configurado para o formato {fmt!r}.")
    parsed = urllib.parse.urlparse(url)
    path = SCHEMAS_DIR / parsed.netloc / parsed.path.lstrip("/")
    if not path.exists():
        raise SchemaNotAvailable(f"{path} não existe. Rode `python manage.py fetch_metadata_schemas`.")
    return path


@functools.lru_cache(maxsize=None)
def get_schema(fmt):
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    return etree.XMLSchema(etree.parse(str(_schema_path(fmt)), parser))


def validate_xml(xml, fmt=ISO19115_3):
    """
    Valida ``xml`` (str ou bytes) contra o XSD do formato.

    Devolve a lista de erros, vazia se o documento for válido. Cada erro é
    ``"linha N: mensagem"``.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    try:
        doc = etree.fromstring(xml, etree.XMLParser(no_network=True, resolve_entities=False))
    except etree.XMLSyntaxError as err:
        return [f"XML mal formado: {err}"]
    schema = get_schema(fmt)
    if schema.validate(doc):
        return []
    return [f"linha {e.line}: {e.message}" for e in schema.error_log]
