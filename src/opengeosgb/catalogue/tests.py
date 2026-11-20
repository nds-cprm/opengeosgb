"""
Testes do app opengeosgb.catalogue.

    python manage.py test opengeosgb.catalogue
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from lxml import etree

from geonode.base.models import ResourceBase
from geonode.catalogue import get_catalogue
from geonode.catalogue.models import catalogue_post_save, update_csw_metadata
from geonode.layers.models import Dataset

from . import views
from .config import build_pycsw_config
from .constants import ISO19115_3, ISO19139, METADATA_TEMPLATES
from .formats import METADATA_FORMATS, format_of_xml

ENGINE = "opengeosgb.catalogue.backends.pycsw_local"
CATALOGUE_SETTINGS = {"default": {**settings.CATALOGUE["default"], "ENGINE": ENGINE}}

MDB = METADATA_FORMATS[ISO19115_3][1]
GMD = METADATA_FORMATS[ISO19139][1]


def _format_settings(fmt):
    return override_settings(
        CATALOGUE=CATALOGUE_SETTINGS,
        CATALOGUE_DEFAULT_FORMAT=fmt,
        CATALOG_METADATA_TEMPLATE=METADATA_TEMPLATES[fmt],
    )


class PycswConfigTest(TestCase):
    def test_config_is_fresh_on_each_call(self):
        first = build_pycsw_config()
        first["repository"]["filter"] += " AND id = 1"
        self.assertEqual(build_pycsw_config()["repository"]["filter"], "uuid IS NOT NULL")

    def test_settings_win_and_profiles(self):
        config = build_pycsw_config()
        self.assertEqual(config["server"]["maxrecords"], settings.PYCSW["CONFIGURATION"]["server"]["maxrecords"])
        self.assertIn("home", config["server"])  # padrão do núcleo mantido
        self.assertTrue({"apiso", "ebrim", "iso19115p3"} <= config["profiles"])


class CatalogueTestBase(TestCase):
    """Usuário e utilitários comuns; sem testes próprios."""

    def setUp(self):
        self.owner = get_user_model().objects.filter(is_superuser=True).first() or get_user_model().objects.create(
            username="catalogue_admin", is_superuser=True
        )

    def _dataset(self, name):
        return Dataset.objects.create(
            owner=self.owner,
            name=name,
            title=f"Título {name}",
            abstract="Resumo",
            subtype="vector",
            alternate=f"geonode:{name}",
            workspace="geonode",
            bbox_polygon="SRID=4326;POLYGON((-50 -20,-50 -10,-40 -10,-40 -20,-50 -20))",
            srid="EPSG:4326",
        )

    def _stored(self, dataset):
        return ResourceBase.objects.values("csw_typename", "csw_schema", "metadata_xml").get(pk=dataset.pk)

    def _get_record_by_id(self, uuid, outputschema):
        request = RequestFactory().get(
            "/catalogue/csw",
            {
                "service": "CSW",
                "version": "2.0.2",
                "request": "GetRecordById",
                "id": uuid,
                "outputschema": outputschema,
                "elementsetname": "full",
            },
        )
        request.user = self.owner
        response = views.csw_global_dispatch(request, dataset_filter=None)
        self.assertEqual(response.status_code, 200)
        return etree.fromstring(response.content)


class CatalogueFormatTest(CatalogueTestBase):
    def test_iso19115_3(self):
        with _format_settings(ISO19115_3):
            dataset = self._dataset("ds_mdb")
            catalogue_post_save(instance=dataset, sender=Dataset)
            stored = self._stored(dataset)
            self.assertEqual(stored["csw_typename"], "mdb:MD_Metadata")
            self.assertEqual(stored["csw_schema"], MDB)
            self.assertEqual(format_of_xml(stored["metadata_xml"]), ISO19115_3)

            record = get_catalogue().get_record(dataset.uuid)
            self.assertIsNotNone(record)
            self.assertEqual(record.identification[0].title, dataset.title)
            self.assertIn(ISO19115_3, [name for _mime, name, _url in record.links["metadata"]])

            # o XML gravado sai como está pelo perfil iso19115p3
            root = self._get_record_by_id(dataset.uuid, MDB)
            self.assertIsNotNone(root.find(f"{{{MDB}}}MD_Metadata"))
            # e o apiso continua entregando ISO 19139, gerado a partir das colunas
            root = self._get_record_by_id(dataset.uuid, GMD)
            self.assertIsNotNone(root.find(f"{{{GMD}}}MD_Metadata"))

    def test_iso19139_and_format_switch(self):
        with _format_settings(ISO19139):
            dataset = self._dataset("ds_gmd")
            catalogue_post_save(instance=dataset, sender=Dataset)
            stored = self._stored(dataset)
            self.assertEqual(stored["csw_typename"], "gmd:MD_Metadata")
            self.assertEqual(format_of_xml(stored["metadata_xml"]), ISO19139)
            self.assertIsNotNone(get_catalogue().get_record(dataset.uuid))

        # caminho do editor de metadados: save() + update_csw_metadata(), sem catalogue_post_save
        with _format_settings(ISO19115_3):
            resource = ResourceBase.objects.get(pk=dataset.pk)
            resource.save()
            update_csw_metadata(resource)
            stored = self._stored(dataset)
            self.assertEqual(stored["csw_typename"], "mdb:MD_Metadata")
            self.assertEqual(format_of_xml(stored["metadata_xml"]), ISO19115_3)

    def test_scale_in_xml(self):
        from opengeosgb.metadata.fields import SCALE_FIELD
        from geonode.metadata.models import SparseField

        for fmt in (ISO19139, ISO19115_3):
            with self.subTest(fmt=fmt), _format_settings(fmt):
                dataset = self._dataset(f"ds_scale_{fmt.lower().replace('-', '_')}")
                SparseField.objects.update_or_create(
                    resource=dataset, name=SCALE_FIELD, defaults={"value": '{"id": 250000, "label": "1:250.000"}'}
                )
                catalogue_post_save(instance=dataset, sender=Dataset)
                xml = self._stored(dataset)["metadata_xml"]
                self.assertIn("250000", xml)
                self.assertIn("denominator", xml)


class MetadataXsdTest(CatalogueTestBase):
    """O XML ISO 19115-3 gerado pelo template é válido contra o XSD (mdb 2.0)."""

    def test_iso19115_3_is_valid(self):
        from geonode.base.models import Region
        from geonode.metadata.models import SparseField
        from opengeosgb.metadata.fields import SCALE_FIELD

        from .validation import validate_xml

        with _format_settings(ISO19115_3):
            minimal = self._dataset("ds_xsd_min")
            catalogue_post_save(instance=minimal, sender=Dataset)

            full = self._dataset("ds_xsd_full")
            full.keywords.add("geologia")
            full.regions.add(*Region.objects.all()[:1])
            full.purpose = "Propósito"
            full.supplemental_information = "Informação complementar"
            full.data_quality_statement = "Qualidade"
            full.constraints_other = "Uso livre"
            full.save()
            full.add_missing_metadata_author_or_poc()  # contatos, como no fluxo real de criação
            SparseField.objects.update_or_create(
                resource=full, name=SCALE_FIELD, defaults={"value": '{"id": 100000, "label": "1:100.000"}'}
            )
            catalogue_post_save(instance=full, sender=Dataset)

            for dataset in (minimal, full):
                with self.subTest(dataset=dataset.name):
                    errors = validate_xml(self._stored(dataset)["metadata_xml"], ISO19115_3)
                    self.assertEqual(errors, [], "\n".join(errors))


class GetDomainTest(CatalogueTestBase):
    def _get_domain(self, propertyname):
        request = RequestFactory().get(
            "/catalogue/csw",
            {"service": "CSW", "version": "2.0.2", "request": "GetDomain", "propertyname": propertyname},
        )
        request.user = self.owner
        response = views.csw_global_dispatch(request, dataset_filter=None)
        self.assertEqual(response.status_code, 200)
        root = etree.fromstring(response.content)
        return [v.text for v in root.iter("{http://www.opengis.net/cat/csw/2.0.2}Value")]

    def test_get_domain_lists_values_with_counts(self):
        with _format_settings(ISO19115_3):
            for name in ("ds_dom_a", "ds_dom_b"):
                catalogue_post_save(instance=self._dataset(name), sender=Dataset)
            values = self._get_domain("dc:title")
        self.assertIn("Título ds_dom_a (1)", values)
        self.assertIn("Título ds_dom_b (1)", values)

    def test_repository_query_domain(self):
        from .backends.pycsw_repository import GeoNodeRepository

        for name in ("ds_rng_a", "ds_rng_b"):
            self._dataset(name)
        repo = GeoNodeRepository.__new__(GeoNodeRepository)
        repo.filter = "title IN ('Título ds_rng_a', 'Título ds_rng_b')"

        self.assertEqual(repo.query_domain("title", None, "range"), [("Título ds_rng_a", "Título ds_rng_b")])
        self.assertEqual(
            repo.query_domain("title", None, "list", count=True), [("Título ds_rng_a", 1), ("Título ds_rng_b", 1)]
        )
        self.assertEqual(repo.query_domain("title", None, "list"), [("Título ds_rng_a",), ("Título ds_rng_b",)])


class CswFilterTest(TestCase):
    def test_clauses_are_anded(self):
        request = RequestFactory().get("/catalogue/csw")
        request.user = get_user_model().objects.create(username="csw_user")
        with override_settings(GROUP_PRIVATE_RESOURCES=True):
            where = views._repository_filter(request, "uuid IS NOT NULL", None)
        self.assertNotIn(" OR (id", where)
        self.assertTrue(where.startswith("(uuid IS NOT NULL) AND (id"))
        self.assertIn("group_id", where)


# ---------------------------------------------------------------------------
# Dataset fictício completo
# ---------------------------------------------------------------------------

NS = {
    "mdb": MDB,
    "mri": "http://standards.iso.org/iso/19115/-3/mri/1.0",
    "mrd": "http://standards.iso.org/iso/19115/-3/mrd/1.0",
    "mrl": "http://standards.iso.org/iso/19115/-3/mrl/2.0",
    "mco": "http://standards.iso.org/iso/19115/-3/mco/1.0",
    "mcc": "http://standards.iso.org/iso/19115/-3/mcc/1.0",
    "cit": "http://standards.iso.org/iso/19115/-3/cit/2.0",
    "gex": "http://standards.iso.org/iso/19115/-3/gex/1.0",
    "gco": "http://standards.iso.org/iso/19115/-3/gco/1.0",
}

FICTITIOUS = {
    "title": "Mapa Geológico da Folha Serra do Exemplo",
    "abstract": "Mapa geológico fictício na escala 1:250.000, usado nos testes do catálogo.",
    "purpose": "Testar a geração do XML de metadados com todos os campos preenchidos.",
    "data_quality_statement": "Compilado a partir de levantamentos de campo fictícios (2020-2024).",
    "supplemental_information": "Dados fictícios: não use para nenhuma finalidade real.",
    "constraints_other": "Uso livre, com citação da fonte.",
    "doi": "10.99999/opengeosgb.exemplo",
    "edition": "2ª edição",
    "bbox": (-48.0, -16.0, -47.0, -15.0),  # x0, y0, x1, y1 (EPSG:4326)
    "scale": 250000,
    "keywords": ["geologia", "litoestratigrafia"],
}


def create_fictitious_dataset(name="mapa_geologico_serra_do_exemplo", subtype="vector", approved=True):
    """
    Cria, pelo fluxo real do GeoNode (``resource_manager.create``), um dataset
    fictício com todos os campos que o template de metadados usa. Só a
    sincronização com o GeoServer é desligada, porque não há GeoServer nos testes.
    """
    from unittest import mock

    from django.contrib.gis.geos import Polygon

    from geonode.base.models import (
        License,
        Link,
        Region,
        RestrictionCodeType,
        SpatialRepresentationType,
        Thesaurus,
        ThesaurusKeyword,
        ThesaurusKeywordLabel,
        TopicCategory,
    )
    from geonode.metadata.models import SparseField
    from geonode.resource.manager import resource_manager
    from opengeosgb.metadata.fields import SCALE_FIELD

    owner, _ = get_user_model().objects.get_or_create(
        username="geologa_exemplo",
        defaults=dict(
            first_name="Maria",
            last_name="Exemplo",
            email="maria.exemplo@example.org",
            organization="Serviço Geológico Fictício",
            position="Pesquisadora em Geociências",
            voice="+55 21 0000-0000",
            fax="+55 21 0000-0001",
            delivery="Av. Exemplo, 100",
            city="Rio de Janeiro",
            area="RJ",
            zipcode="22000-000",
            country="BRA",
            is_superuser=True,
        ),
    )
    category, _ = TopicCategory.objects.get_or_create(
        identifier="geoscientificInformation",
        defaults=dict(description="Geoscientific information", gn_description="Informações geocientíficas"),
    )
    license_, _ = License.objects.get_or_create(
        identifier="cc-by-4.0",
        defaults=dict(
            name="Creative Commons Atribuição 4.0",
            abbreviation="CC-BY-4.0",
            url="https://creativecommons.org/licenses/by/4.0/",
            description="Permite uso com atribuição.",
        ),
    )
    restriction, _ = RestrictionCodeType.objects.get_or_create(
        identifier="otherRestrictions", defaults=dict(description="other restrictions", gn_description="Outras")
    )
    representation, _ = SpatialRepresentationType.objects.get_or_create(
        identifier="vector" if subtype == "vector" else "grid",
        defaults=dict(description=subtype, gn_description=subtype),
    )
    region, _ = Region.objects.get_or_create(code="BRA", defaults=dict(name="Brasil"))
    thesaurus, _ = Thesaurus.objects.get_or_create(
        identifier="opengeosgb-exemplo",
        defaults=dict(title="Tesauro fictício de geociências", date="2024-01-01", description="Fictício"),
    )
    tkeyword, _ = ThesaurusKeyword.objects.get_or_create(
        thesaurus=thesaurus, alt_label="granito", defaults=dict(about="https://example.org/tesauro/granito")
    )
    ThesaurusKeywordLabel.objects.get_or_create(keyword=tkeyword, lang="pt", defaults=dict(label="Granito"))
    ThesaurusKeywordLabel.objects.get_or_create(keyword=tkeyword, lang="en", defaults=dict(label="Granite"))

    x0, y0, x1, y1 = FICTITIOUS["bbox"]
    polygon = Polygon.from_bbox((x0, y0, x1, y1))
    polygon.srid = 4326
    with mock.patch("geonode.geoserver.manager.sync_instance_with_geoserver", return_value=None):
        dataset = resource_manager.create(
            None,
            resource_type=Dataset,
            defaults=dict(
                owner=owner,
                name=name,
                title=FICTITIOUS["title"] + ("" if subtype == "vector" else " (raster)"),
                abstract=FICTITIOUS["abstract"],
                purpose=FICTITIOUS["purpose"],
                data_quality_statement=FICTITIOUS["data_quality_statement"],
                supplemental_information=FICTITIOUS["supplemental_information"],
                constraints_other=FICTITIOUS["constraints_other"],
                restriction_code_type=restriction,
                doi=FICTITIOUS["doi"],
                edition=FICTITIOUS["edition"],
                language="por",
                date_type="publication",
                maintenance_frequency="asNeeded",
                category=category,
                license=license_,
                spatial_representation_type=representation,
                subtype=subtype,
                workspace="geonode",
                alternate=f"geonode:{name}",
                srid="EPSG:4326",
                bbox_polygon=polygon,
                ll_bbox_polygon=polygon,
                is_approved=approved,
                is_published=approved,
            ),
        )

    dataset.keywords.add(*FICTITIOUS["keywords"])
    dataset.tkeywords.add(tkeyword)
    dataset.regions.add(region)
    SparseField.objects.update_or_create(
        resource=dataset, name=SCALE_FIELD, defaults={"value": f'{{"id": {FICTITIOUS["scale"]}, "label": "1:250.000"}}'}
    )
    base = f"https://geoserver.example.org/geoserver/ows?layers=geonode:{name}"
    Link.objects.get_or_create(
        resource=dataset, link_type="data", extension="zip",
        defaults=dict(name="Zipped Shapefile", mime="SHAPE-ZIP", url=f"{base}&outputFormat=SHAPE-ZIP"),
    )
    Link.objects.get_or_create(
        resource=dataset, link_type="OGC:WMS", extension="html",
        defaults=dict(name=name, mime="text/html", url=f"{base}&service=WMS"),
    )
    # regera o XML com as palavras-chave, regiões, links e escala acrescentados depois da criação
    dataset.refresh_from_db()
    catalogue_post_save(instance=dataset, sender=Dataset)
    dataset.refresh_from_db()
    return dataset


def _texts(root, path):
    return [(e.text or "").strip() for e in root.xpath(path, namespaces=NS)]


class FictitiousDatasetTest(TestCase):
    """Inclusão de um dataset fictício completo, do cadastro ao CSW."""

    def _xml(self, dataset):
        return etree.fromstring(ResourceBase.objects.get(pk=dataset.pk).metadata_xml.encode("utf-8"))

    def test_created_through_resource_manager(self):
        with _format_settings(ISO19115_3):
            dataset = create_fictitious_dataset()
        stored = ResourceBase.objects.get(pk=dataset.pk)
        self.assertEqual(stored.csw_typename, "mdb:MD_Metadata")
        self.assertEqual(format_of_xml(stored.metadata_xml), ISO19115_3)
        # set_missing_info cria os contatos obrigatórios a partir do dono
        self.assertTrue(dataset.contactrole_set.exists())
        self.assertTrue(stored.link_set.filter(link_type="metadata", name=ISO19115_3).exists())

    def test_iso19115_3_content(self):
        from django.utils import translation

        # os rótulos do tesauro saem no idioma ativo de quem salva o recurso
        with _format_settings(ISO19115_3), translation.override("pt-br"):
            dataset = create_fictitious_dataset()
        root = self._xml(dataset)
        ident = "mdb:identificationInfo/mri:MD_DataIdentification"

        self.assertEqual(_texts(root, f"{ident}/mri:citation/cit:CI_Citation/cit:title/gco:CharacterString"), [dataset.title])
        self.assertIn(FICTITIOUS["abstract"], _texts(root, f"{ident}/mri:abstract/gco:CharacterString"))
        self.assertEqual(_texts(root, f"{ident}/mri:purpose/gco:CharacterString"), [FICTITIOUS["purpose"]])

        keywords = _texts(root, f"{ident}/mri:descriptiveKeywords/mri:MD_Keywords/mri:keyword/gco:CharacterString")
        for expected in FICTITIOUS["keywords"] + ["Brasil", "Granito"]:
            self.assertIn(expected, keywords)

        self.assertEqual(
            _texts(root, f"{ident}/mri:spatialResolution/mri:MD_Resolution/mri:equivalentScale//gco:Integer"),
            [str(FICTITIOUS["scale"])],
        )
        bbox = root.xpath(f"{ident}/mri:extent//gex:EX_GeographicBoundingBox", namespaces=NS)[0]
        x0, y0, x1, y1 = FICTITIOUS["bbox"]
        for tag, value in (("westBoundLongitude", x0), ("eastBoundLongitude", x1), ("southBoundLatitude", y0), ("northBoundLatitude", y1)):
            self.assertAlmostEqual(float(_texts(bbox, f"gex:{tag}/gco:Decimal")[0]), value)

        self.assertIn(FICTITIOUS["doi"], etree.tostring(root, encoding="unicode"))
        self.assertIn(FICTITIOUS["constraints_other"], _texts(root, f"{ident}/mri:resourceConstraints//gco:CharacterString"))
        self.assertEqual(
            _texts(root, "mdb:resourceLineage/mrl:LI_Lineage/mrl:statement/gco:CharacterString"),
            [FICTITIOUS["data_quality_statement"]],
        )
        self.assertIn("maria.exemplo@example.org", _texts(root, "mdb:contact//cit:electronicMailAddress/gco:CharacterString"))

        urls = _texts(root, "mdb:distributionInfo//mrd:onLine/cit:CI_OnlineResource/cit:linkage/gco:CharacterString")
        self.assertTrue(any("SHAPE-ZIP" in u for u in urls), urls)
        self.assertTrue(any("service=WMS" in u for u in urls), urls)

    def test_iso19115_3_is_valid_for_all_variants(self):
        from .validation import validate_xml

        variants = [
            ("vetor, licença light", "vector", {"ENABLED": True, "METADATA": "light"}),
            ("vetor, licença verbose", "vector", {"ENABLED": True, "METADATA": "verbose"}),
            ("raster, sem licença no XML", "raster", {"ENABLED": True, "METADATA": "never"}),
        ]
        for i, (label, subtype, licenses) in enumerate(variants):
            with self.subTest(label), _format_settings(ISO19115_3), override_settings(LICENSES=licenses):
                dataset = create_fictitious_dataset(name=f"exemplo_{i}", subtype=subtype)
                errors = validate_xml(ResourceBase.objects.get(pk=dataset.pk).metadata_xml, ISO19115_3)
                self.assertEqual(errors, [], "\n".join(errors))

    def test_iso19139_content(self):
        from owslib.iso import MD_Metadata

        with _format_settings(ISO19139):
            dataset = create_fictitious_dataset()
        record = MD_Metadata(etree.fromstring(ResourceBase.objects.get(pk=dataset.pk).metadata_xml.encode("utf-8")))
        self.assertEqual(record.identification[0].title, dataset.title)
        self.assertIn("geologia", [k.name for kw in record.identification[0].keywords for k in kw.keywords])
        self.assertIn(str(FICTITIOUS["scale"]), [str(d) for d in record.identification[0].denominators])

    def test_csw_delivers_only_complete_approved_datasets(self):
        with _format_settings(ISO19115_3):
            published = create_fictitious_dataset()
            draft = create_fictitious_dataset(name="rascunho_exemplo", approved=False)

            request = RequestFactory().get(
                "/catalogue/csw",
                {
                    "service": "CSW",
                    "version": "2.0.2",
                    "request": "GetRecords",
                    "typenames": "mdb:MD_Metadata",
                    "resulttype": "results",
                    "elementsetname": "full",
                    "outputschema": MDB,
                    "maxrecords": "50",
                },
            )
            request.user = published.owner
            response = views.csw_global_dispatch(request)  # com o filtro padrão do opengeosgb
        self.assertEqual(response.status_code, 200)
        root = etree.fromstring(response.content)
        ids = _texts(root, "//mdb:MD_Metadata/mdb:metadataIdentifier/mcc:MD_Identifier/mcc:code/gco:CharacterString")
        self.assertIn(published.uuid, ids)
        self.assertNotIn(draft.uuid, ids)
