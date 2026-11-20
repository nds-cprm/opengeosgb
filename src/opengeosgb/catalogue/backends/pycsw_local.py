"""
Backend de catálogo do opengeosgb (``CATALOGUE_ENGINE``).

Herda do ``pycsw_local`` do GeoNode 5.0.x e troca o que lá está fixo em ISO 19139:
- o ``outputschema`` e a classe ``MD_Metadata`` do owslib seguem
  ``CATALOGUE_DEFAULT_FORMAT``;
- os links de metadados incluem o ISO 19115-3;
- a configuração do pycsw vem de ``config.build_pycsw_config()``;
- ``create_record``, chamado pelo ``catalogue_post_save`` em todos os caminhos
  (signal, ``set_resource_links``, ``regenerate_xml``...), grava
  ``csw_typename`` e ``csw_schema`` de acordo com o formato.

Correções em relação ao núcleo:
- o ``Catalogue`` fica na instância; o ``__init__`` do núcleo o grava na classe
  (``GenericCatalogueBackend.__init__(CatalogueBackend, self, ...)``), e ele
  passa a ser compartilhado por todas as instâncias;
- ``search_records`` chamava ``.items()`` numa lista.

``get_record``, ``search_records`` e ``_csw_local_dispatch`` são cópias
adaptadas do GeoNode 5.0.x: ao atualizar o GeoNode, compare-os com
``geonode/catalogue/backends/pycsw_local.py``.
"""

import os

from owslib.etree import etree as dlxml
from pycsw import server
from shapely.errors import ShapelyError

from geonode.catalogue.backends import pycsw_local as core
from geonode.catalogue.backends.generic import Catalogue as GenericCatalogue

from ..config import build_pycsw_config
from ..formats import METADATA_FORMATS, csw_format_fields, default_format, default_schema, md_metadata_class

CSW_NAMESPACE = "http://www.opengis.net/cat/csw/2.0.2"


class Catalogue(GenericCatalogue):
    def urls_for_uuid(self, uuid):
        """URLs de GetRecordById de um registro, uma por formato."""
        return [
            ("text/xml", mformat, self.url_for_uuid(uuid, METADATA_FORMATS[mformat][1])) for mformat in self.formats
        ]

    def metadatarecord2dict(self, rec):
        result = super().metadatarecord2dict(rec)
        if result is not None:
            result["metadata_links"] = [("text/xml", default_format(), self.url_for_uuid(rec.identifier, default_schema()))]
        return result


class CatalogueBackend(core.CatalogueBackend):
    def __init__(self, *args, **kwargs):
        self.catalogue = Catalogue(*args, **kwargs)
        self.catalogue.formats = list(METADATA_FORMATS)
        self.catalogue.local = True

    def create_record(self, item):
        from geonode.base.models import ResourceBase

        fields = csw_format_fields(item)
        ResourceBase.objects.filter(pk=item.pk).update(**fields)
        for name, value in fields.items():
            setattr(item, name, value)

    def get_record(self, uuid):
        results = self._csw_local_dispatch(identifier=uuid)
        if len(results) < 1:
            return None

        result = dlxml.fromstring(results).find(f"{{{default_schema()}}}MD_Metadata")
        if result is None:
            return None

        record = md_metadata_class()(result)
        record.keywords = []
        if hasattr(record, "identification") and record.identification and hasattr(record.identification[0], "keywords"):
            for kw in record.identification[0].keywords:
                record.keywords.extend([_kw.name for _kw in kw.keywords])

        record.links = {}
        record.links["metadata"] = self.catalogue.urls_for_uuid(uuid)
        record.links["download"] = self.catalogue.extract_links(record)
        return record

    def search_records(self, keywords, start, limit, bbox):
        with self.catalogue:
            lresults = self._csw_local_dispatch(keywords, start + 1, limit, bbox)
            e = dlxml.fromstring(lresults)

            MD_Metadata = md_metadata_class()
            self.catalogue.records = [MD_Metadata(x) for x in e.findall(f"//{{{default_schema()}}}MD_Metadata")]
            results = [self.catalogue.metadatarecord2dict(doc) for doc in self.catalogue.records]

            search_results = e.find(f"{{{CSW_NAMESPACE}}}SearchResults")
            return {
                "rows": results,
                "total": search_results.attrib.get("numberOfRecordsMatched"),
                "next_page": search_results.attrib.get("nextRecord"),
            }

    def _csw_local_dispatch(self, keywords=None, start=0, limit=10, bbox=None, identifier=None):
        """CSW sem HTTP"""
        mdict = build_pycsw_config()

        # fake HTTP environment variable
        os.environ["QUERY_STRING"] = ""

        csw = server.Csw(mdict, version="2.0.2")
        csw.requesttype = "GET"

        if identifier is None:  # GetRecords
            csw.kvp = {
                "service": "CSW",
                "version": "2.0.2",
                "elementsetname": "full",
                "typenames": [METADATA_FORMATS[f][0] for f in self.catalogue.formats],
                "resulttype": "results",
                "constraintlanguage": "CQL_TEXT",
                "outputschema": default_schema(),
                "constraint": None,
                "startposition": start,
                "maxrecords": limit,
            }
            response = csw.getrecords2()
        else:  # GetRecordById
            csw.kvp = {
                "service": "CSW",
                "version": "2.0.2",
                "request": "GetRecordById",
                "id": identifier,
                "outputschema": default_schema(),
            }
            # o pycsw ainda falha com geometrias vazias (mesmo contorno do núcleo)
            try:
                response = csw.dispatch()
            except ShapelyError:
                return []

        if isinstance(response, list):  # pycsw 2.0+
            response = response[1]

        return response
