"""
Conteúdo da página de visualização de metadados (/metadata/<pk> e /metadata/<pk>/embed).

Substitui o agrupamento genérico da view do geonode-mapstore-client por seções fixas,
valores formatados (datas, extensão, opções) e informações que a view original não mostra:
contatos por pessoa, dicionário de dados, citação e links de distribuição agrupados.
"""
import datetime
import logging
import re
import warnings
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from django.conf import settings
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from geonode.base.auth import get_or_create_token
from geonode.base.models import License, ResourceBase
from geonode.geoserver.helpers import ogc_server_settings
from geonode.metadata.handlers.contact import ROLE_NAMES_MAP
from geonode.metadata.manager import metadata_manager
from geonode.people import Roles
from geonode.utils import build_absolute_uri

from .i18n import normalize_text

logger = logging.getLogger(__name__)

# Seções (chave, título) e os campos do schema que cada uma exibe, na ordem
SECTIONS = [
    ("identification", gettext_lazy("Identification"), [
        "purpose", "category", "tkeywords", "hkeywords", "language", "edition", "attribution",
        "doi", "linkedresources", "supplemental_information",
    ]),
    ("extent", gettext_lazy("Extent"), [
        "regions", "temporal_extent_start", "temporal_extent_end", "scale",
        "spatial_representation_type", "maintenance_frequency",
    ]),
    ("constraints", gettext_lazy("Constraints and license"), ["license", "restriction_code_type", "constraints_other"]),
    ("quality", gettext_lazy("Data quality"), ["data_quality_statement"]),
]

# Campos exibidos fora das seções (cabeçalho, contatos, registro) ou que não devem aparecer
CONSUMED_FIELDS = {"title", "abstract", "date", "date_type", "contacts", "uuid"}

# Formatos de metadados (Link.name -> chave usada no template e rótulo). O template escolhe
# quais exibir (snippets/metadata_view.html)
METADATA_FORMATS = {
    "Dublin Core": ("dublin_core", "Dublin Core"),
    "ISO": ("iso19139", "ISO 19139"),
    "ISO19115-3_2018": ("iso19115_3", "ISO 19115-3:2018"),
    "ISO with XSL": ("iso19139_html", gettext_lazy("ISO 19139 (HTML view)")),
    "Atom": ("atom", "Atom"),
    "DIF": ("dif", "DIF"),
    "ebRIM": ("ebrim", "ebRIM"),
    "FGDC": ("fgdc", "FGDC"),
}

# Tipos de asset (arquivo enviado) -> nome do formato
ASSET_TYPES = {
    "shp": "Shapefile", "gpkg": "GeoPackage", "tif": "GeoTIFF", "tiff": "GeoTIFF", "geojson": "GeoJSON",
    "json": "GeoJSON", "kml": "KML", "kmz": "KMZ", "csv": "CSV", "xlsx": "Excel", "xls": "Excel",
    "zip": "ZIP", "pdf": "PDF", "3dtiles": "3D Tiles",
}

# Tipos de atributo (xsd/gml) -> descrição
ATTRIBUTE_TYPES = {
    "int": gettext_lazy("Integer"), "integer": gettext_lazy("Integer"), "long": gettext_lazy("Integer"),
    "short": gettext_lazy("Integer"), "double": gettext_lazy("Decimal"), "float": gettext_lazy("Decimal"),
    "decimal": gettext_lazy("Decimal"), "string": gettext_lazy("Text"), "boolean": gettext_lazy("Boolean"),
    "date": gettext_lazy("Date"), "datetime": gettext_lazy("Date/time"), "time": gettext_lazy("Time of day"),
}


def format_date(value):
    """Data ou data/hora no formato curto do idioma ativo (ex.: 06/11/2026)."""
    if isinstance(value, datetime.datetime):
        value = timezone.localtime(value) if timezone.is_aware(value) else value
        return formats.date_format(value, "SHORT_DATETIME_FORMAT")
    if isinstance(value, datetime.date):
        return formats.date_format(value, "SHORT_DATE_FORMAT")
    return value


def _is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def _text(value):
    """Texto puro a partir de HTML, mantendo parágrafos e quebras de linha."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
        text = BeautifulSoup(unescape(str(value)), "html.parser").get_text("\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return text or None


def _clean(value):
    """Valor de perfil de usuário, tratando o texto "None" gravado em alguns cadastros como vazio."""
    return None if value in (None, "", "None") else value


def display_value(value, schema):
    """
    Valor do schema instance pronto para exibição: texto, data, lista ou link
    ({"url", "text"}). Retorna None quando não há o que mostrar.
    """
    if _is_empty(value):
        return None
    schema = schema or {}

    if "oneOf" in schema:
        for option in schema["oneOf"]:
            if option.get("const") == value:
                return option.get("title") or value
        return value

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((t for t in schema_type if t != "null"), None)

    if schema_type == "array" or isinstance(value, list):
        items = [display_value(item, schema.get("items")) for item in value]
        return [item for item in items if item is not None] or None

    if schema_type == "object" or isinstance(value, dict):
        if "label" in value:
            return _text(value["label"]) if value.get("label") else None
        # objeto genérico (ex.: palavras-chave por tesauro): achata em lista
        items = []
        for key, sub_value in value.items():
            sub_schema = schema.get("properties", {}).get(key, {})
            shown = display_value(sub_value, sub_schema)
            if isinstance(shown, list):
                items.extend(shown)
            elif shown is not None:
                items.append(shown)
        return items or None

    if isinstance(value, (datetime.date, datetime.datetime)):
        return format_date(value)
    if schema.get("format") == "date" and isinstance(value, str):
        return format_date(parse_date(value) or value)
    if schema.get("format") == "date-time" and isinstance(value, str):
        return format_date(parse_datetime(value) or value)

    if isinstance(value, str):
        return _text(value)
    return value


def _field_row(name, instance, properties):
    value = display_value(instance.get(name), properties.get(name))
    if value is None:
        return None
    if name == "license":
        url = License.objects.filter(identifier=instance[name].get("id")).values_list("url", flat=True).first()
        if url:
            value = {"url": url, "text": value}
    if name == "doi":
        value = {"url": f"https://doi.org/{value}", "text": value}
    if name == "linkedresources":
        value = [
            {"url": reverse("metadata", args=[item["id"]]), "text": _text(item.get("label")) or item["id"]}
            for item in instance[name]
            if item.get("id")
        ]
    return {"name": name, "label": properties[name].get("title", name), "value": value}


def _format_coordinate(value):
    return formats.number_format(round(value, 4), 4) + "°"


def _extent_rows(resource):
    rows = []
    try:
        x0, x1, y0, y1 = (float(v) for v in resource.ll_bbox[:4])
        rows.append({
            "name": "geographic_extent",
            "label": _("Geographic extent"),
            "value": [
                f"{_('West')}: {_format_coordinate(x0)}",
                f"{_('East')}: {_format_coordinate(x1)}",
                f"{_('South')}: {_format_coordinate(y0)}",
                f"{_('North')}: {_format_coordinate(y1)}",
            ],
        })
    except (TypeError, ValueError, IndexError):
        pass

    if resource.srid:
        srs = resource.srid
        try:
            from django.contrib.gis.gdal import SpatialReference

            name = SpatialReference(int(str(resource.srid).split(":")[-1])).name
            srs = f"{resource.srid} ({name})"
        except Exception:
            pass
        rows.append({"name": "reference_system", "label": _("Reference system"), "value": srs})
    return rows


def _contacts(resource):
    """Pessoas associadas ao recurso, cada uma com seus papéis."""
    people = {}
    for role, rolename in ROLE_NAMES_MAP.items():
        users = [resource.owner] if role == Roles.OWNER else (resource.__get_contact_role_elements__(rolename) or [])
        for user in users:
            entry = people.setdefault(user.pk, {"user": user, "roles": []})
            entry["roles"].append(_(role.label))
    return [
        {
            # nome completo, sem o "(login)" que o name_long do GeoNode acrescenta
            "name": entry["user"].get_full_name().strip() or entry["user"].username,
            "position": _clean(entry["user"].position),
            "organization": _clean(entry["user"].organization),
            "email": _clean(entry["user"].email),
            "roles": entry["roles"],
        }
        for entry in people.values()
    ]


def _data_dictionary(resource):
    attributes = getattr(resource, "attributes", None)
    if attributes is None:
        return []
    rows = []
    for attribute in attributes.filter(visible=True).order_by("display_order"):
        raw_type = (attribute.attribute_type or "").split(":")[-1]
        if raw_type.lower().endswith("propertytype"):
            attr_type = f"{_('Geometry')} ({raw_type[:-len('PropertyType')]})"
        else:
            attr_type = ATTRIBUTE_TYPES.get(raw_type.lower(), raw_type)
        rows.append({
            "name": attribute.attribute,
            "type": attr_type,
            "description": attribute.description or attribute.attribute_label or "",
        })
    return rows


def _asset_label(link):
    """Rótulo do asset (arquivo enviado), ex.: "Original — Shapefile (.dbf, .prj, .shp, .shx)"."""
    asset = link.asset
    asset = asset.get_real_instance() if hasattr(asset, "get_real_instance") else asset
    title = _(asset.title or link.name)
    asset_type = ASSET_TYPES.get((asset.type or "").lower(), (asset.type or "").upper())
    extensions = sorted({f".{str(path).rsplit('.', 1)[-1].lower()}" for path in getattr(asset, "location", None) or [] if "." in str(path)})
    detail = f"{asset_type} ({', '.join(extensions)})" if extensions else asset_type
    return f"{title} — {detail}" if detail else title


def _with_access_token(url, access_token):
    """
    Acrescenta o access_token do usuário a URLs do GeoServer: os links abrem direto no GeoServer,
    sem a sessão do GeoNode, e camadas privadas responderiam "Feature type ... unknown".
    """
    if not access_token or not url.startswith(ogc_server_settings.PUBLIC_LOCATION):
        return url
    parts = urlsplit(url)
    params = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() != "access_token"]
    params.append(("access_token", access_token))
    return urlunsplit(parts._replace(query=urlencode(params)))


def _distribution(resource, access_token=None):
    groups = {"metadata": {}, "services": [], "assets": [], "downloads": [], "images": [], "legend": []}
    for link in resource.link_set.exclude(link_type="html").select_related("asset").order_by("name"):
        if link.asset_id:
            # arquivos enviados ao GeoNode (assets), separados dos formatos gerados pelo GeoServer
            groups["assets"].append({"url": link.url, "text": _asset_label(link)})
        elif link.link_type == "metadata":
            key, label = METADATA_FORMATS.get(link.name, (link.name, link.name))
            groups["metadata"][key] = {"url": link.url, "text": label}
        elif link.link_type.startswith("OGC:"):
            groups["services"].append({
                "url": link.url,
                "text": link.link_type.split(":", 1)[1],
                "layer": getattr(resource, "alternate", None),
            })
        elif link.link_type == "data":
            groups["downloads"].append({"url": link.url, "text": _(link.name)})
        elif link.link_type == "image" and link.name == "Legend":
            groups["legend"].append({"url": link.url, "text": _(link.name)})
        elif link.link_type == "image" and link.name != "Thumbnail":
            groups["images"].append({"url": link.url, "text": _(link.name)})
    geopackage = _geopackage_download(groups["downloads"])
    if geopackage:
        groups["downloads"].append(geopackage)
    for name in ("downloads", "images"):
        groups[name].sort(key=lambda item: str(item["text"]).lower())
    # serviços OGC ficam sem token: o endereço é copiado para outros programas (ex.: QGIS)
    for name in ("downloads", "images", "legend"):
        for item in groups[name]:
            item["url"] = _with_access_token(item["url"], access_token)
    return groups


def _geopackage_download(downloads):
    """
    Link de download em GeoPackage, que o GeoNode não gera (formato ausente em geonode/geoserver/ows.py).
    Montado a partir do download WFS em CSV do recurso, trocando apenas o outputFormat; o GeoServer
    precisa da extensão geopkg-output (instalada na imagem do submódulo docker/).
    """
    if any(str(item["text"]).lower() == "geopackage" for item in downloads):
        return None
    for item in downloads:
        parts = urlsplit(item["url"])
        params = parse_qsl(parts.query, keep_blank_values=True)
        output_format = next((value for key, value in params if key.lower() == "outputformat"), "")
        if output_format.lower() != "csv":
            continue
        params = [(key, "geopkg" if key.lower() == "outputformat" else value) for key, value in params]
        return {"url": urlunsplit(parts._replace(query=urlencode(params))), "text": "GeoPackage"}
    return None


def _publisher():
    try:
        return settings.PYCSW["CONFIGURATION"]["metadata"]["provider"]["name"]
    except (AttributeError, KeyError, TypeError):
        return getattr(settings, "SITENAME", "")


def _citation_authors(contacts):
    """Autores da citação: pessoas com papel de originador ou pesquisador principal."""
    author_roles = {_(Roles.ORIGINATOR.label), _(Roles.PRINCIPAL_INVESTIGATOR.label)}
    return [c["name"] for c in contacts if author_roles & set(c["roles"])]


def _citation(resource, contacts):
    authors = _citation_authors(contacts)
    publisher = _publisher()
    citation = _("%(authors)s. %(title)s. %(publisher)s, %(year)s. Available at: %(url)s. Accessed on: %(accessed)s.") % {
        "authors": "; ".join(authors) if authors else publisher,
        "title": resource.title,
        "publisher": publisher,
        "year": resource.date.year if resource.date else "",
        "url": build_absolute_uri(resource.detail_url),
        "accessed": formats.date_format(datetime.date.today(), "SHORT_DATE_FORMAT"),
    }
    if resource.doi:
        citation += f" DOI: {resource.doi}."
    return citation


LATEX_SPECIAL_CHARS = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_", "$": r"\$"}


def _latex_escape(text) -> str:
    return "".join(LATEX_SPECIAL_CHARS.get(char, char) for char in str(text))


def _bibtex(resource, contacts):
    """Referência em BibTeX (@misc, compatível com BibTeX e biblatex)."""
    authors = _citation_authors(contacts)
    publisher = _latex_escape(_publisher())
    # autor institucional entre chaves duplas, para não ser lido como "sobrenome, nome"
    author = " and ".join(_latex_escape(a) for a in authors) if authors else f"{{{publisher}}}"
    year = resource.date.year if resource.date else ""
    key_base = (getattr(resource, "alternate", None) or resource.title).split(":")[-1]
    key = normalize_text(re.sub(r"[^\w]+", "_", key_base)).strip("_") + (f"_{year}" if year else "")
    url = build_absolute_uri(resource.detail_url)
    today = datetime.date.today()

    fields = [
        ("author", f"{{{author}}}"),
        ("title", f"{{{{{_latex_escape(resource.title)}}}}}"),
        ("publisher", f"{{{publisher}}}"),
        ("year", f"{{{year}}}"),
        ("howpublished", f"{{\\url{{{url}}}}}"),
        ("url", f"{{{url}}}"),
    ]
    if resource.doi:
        fields.append(("doi", f"{{{resource.doi}}}"))
    fields += [
        ("urldate", f"{{{today.isoformat()}}}"),
        ("note", f"{{{_latex_escape(_('Accessed on: %(date)s') % {'date': formats.date_format(today, 'SHORT_DATE_FORMAT')})}}}"),
    ]
    width = max(len(name) for name, _value in fields)
    body = ",\n".join(f"  {name.ljust(width)} = {value}" for name, value in fields)
    return f"@misc{{{key},\n{body}\n}}"


def _resource_type_label(resource):
    if resource.resource_type == "dataset":
        return {
            "raster": _("Raster Dataset"),
            "vector": _("Vector Dataset"),
            "remote": _("Remote Dataset"),
        }.get(resource.subtype, _("Dataset"))
    return {
        "map": _("Map"), "document": _("Document"), "geostory": _("GeoStory"), "dashboard": _("Dashboard"),
    }.get(resource.resource_type, resource.resource_type)


def _items(value):
    """Normaliza o valor de uma linha em lista de itens {"text", "url"?} para o template."""
    values = value if isinstance(value, list) else [value]
    return [v if isinstance(v, dict) else {"text": v} for v in values if v not in (None, "")]


def build_metadata_page(resource: ResourceBase, lang: str, user=None) -> dict:
    schema = metadata_manager.get_schema(lang)
    properties = schema["properties"]
    instance = metadata_manager.build_schema_instance(resource, lang)

    sections = []
    used = set(CONSUMED_FIELDS)
    for key, title, fields in SECTIONS:
        rows = [row for row in (_field_row(name, instance, properties) for name in fields if name in properties) if row]
        used.update(fields)
        if key == "extent":
            rows = _extent_rows(resource) + rows
        if rows:
            sections.append({"key": key, "title": title, "rows": rows})

    # campos preenchidos que não estão em nenhuma seção (ex.: campos extras futuros)
    other = [
        row for row in (
            _field_row(name, instance, properties)
            for name in properties if name not in used and name in instance
        ) if row
    ]
    if other:
        sections.append({"title": _("Other information"), "rows": other})

    contacts = _contacts(resource)
    date_type = display_value(instance.get("date_type"), properties.get("date_type"))
    record = [
        {"label": _("Identifier"), "value": str(resource.uuid)},
        {"label": _("Created"), "value": format_date(resource.created)},
        {"label": _("Last updated"), "value": format_date(resource.last_updated)},
        # popular_count não é exibido: no GeoNode 5 só a rota legada de dataset embutido o incrementa
    ]
    for row in [row for section in sections for row in section["rows"]] + record:
        row["items"] = _items(row.pop("value"))

    return {
        "type_label": _resource_type_label(resource),
        "thumbnail_url": resource.thumbnail_url,
        "abstract": _text(resource.abstract) if resource.abstract else None,
        "date": format_date(resource.date.date() if resource.date else None),
        "date_label": f"{properties['date'].get('title', _('Date'))} ({date_type})" if date_type else properties["date"].get("title"),
        "sections": sections,
        "contacts": contacts,
        "data_dictionary": _data_dictionary(resource),
        "citation": _citation(resource, contacts),
        "bibtex": _bibtex(resource, contacts),
        "distribution": _distribution(
            resource, get_or_create_token(user).token if user is not None and user.is_authenticated else None
        ),
        "resource_url": build_absolute_uri(resource.detail_url),
        "record": record,
    }
