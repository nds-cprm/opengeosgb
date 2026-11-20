"""
Filtro do conjunto entregue pelo endpoint CSW do opengeosgb.

Só entram datasets aprovados, publicados e com completude de metadados acima de
``CSW_MIN_METADATA_COMPLETENESS`` (padrão: 60%).

O filtro restringe a lista de IDs autorizados que a view injeta no filtro do
pycsw, então vale para todas as operações (GetRecords, GetRecordById,
GetDomain). Não se usa ``PYCSW["CONFIGURATION"]["repository"]["filter"]``
porque ele também vale para as chamadas internas do ``catalogue_post_save``:
recursos fora do critério deixariam de ter o XML gerado.
"""

from django.conf import settings
from django.db.models import Case, Exists, ExpressionWrapper, F, IntegerField, OuterRef, Q, Value, When

from geonode.base.models import ResourceBase


def _filled(field):
    """Campo de texto preenchido, como no ``if field`` de metadata_completeness."""
    return Q(**{f"{field}__isnull": False}) & ~Q(**{field: ""})


def _point(condition):
    return Case(When(condition, then=Value(1)), default=Value(0), output_field=IntegerField())


_OTHER_RESTRICTIONS = Q(restriction_code_type__identifier="otherRestrictions")


def with_metadata_completeness(queryset):
    """
    Anota ``md_filled`` e ``md_required`` reproduzindo em SQL a propriedade
    ResourceBase.metadata_completeness (geonode/base/models.py). Se a
    propriedade mudar no GeoNode, esta função precisa acompanhar.
    """
    regions = ResourceBase.regions.through.objects.filter(resourcebase_id=OuterRef("pk"))
    filled = (
        _point(_filled("abstract"))
        + _point(_filled("category__identifier"))
        + _point(_filled("data_quality_statement"))
        + _point(Q(date__isnull=False))
        + _point(_filled("date_type"))
        + _point(_filled("language"))
        + _point(Q(license__isnull=False) & ~Q(license__name="Not Specified"))
        + _point(Exists(regions))
        + _point(_filled("title"))
        + _point(_OTHER_RESTRICTIONS & _filled("constraints_other"))
    )
    required = Value(9) + _point(_OTHER_RESTRICTIONS)
    return queryset.annotate(md_filled=filled, md_required=required)


def csw_dataset_filter(queryset):
    """Datasets aprovados, publicados e com completude > mínimo configurado."""
    minimum = getattr(settings, "CSW_MIN_METADATA_COMPLETENESS", 60)
    return (
        with_metadata_completeness(queryset.filter(resource_type="dataset", is_approved=True, is_published=True))
        .annotate(
            md_margin=ExpressionWrapper(
                F("md_filled") * 100 - Value(minimum) * F("md_required"), output_field=IntegerField()
            )
        )
        .filter(md_margin__gt=0)
    )
