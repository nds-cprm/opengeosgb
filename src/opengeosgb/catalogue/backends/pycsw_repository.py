"""
Repositório do pycsw do opengeosgb (``repository.source`` em ``config.py``).

Herda do ``GeoNodeRepository`` do GeoNode 5.0.x e corrige o ``GetDomain``. No
núcleo, ``query_domain`` agrega sobre ``ResourceBase.objects``, um queryset do
django-polymorphic. O polymorphic falha com agregações posicionais
(``annotate(Count(campo))`` e ``aggregate(Min(campo), Max(campo))``):
``AttributeError: 'NoneType' object has no attribute 'name'``, por causa do
``filter=None`` do ``Aggregate``. O pycsw engole a exceção, e todo
``GetDomain`` volta sem valores.

Aqui a consulta usa um ``QuerySet`` comum do Django sobre o mesmo modelo, com
as agregações nomeadas e ordem por valor. Ao atualizar o GeoNode, compare com
``geonode/catalogue/backends/pycsw_plugin.py``.
"""

from django.db.models import Count, Max, Min, QuerySet

from geonode.base.models import ResourceBase
from geonode.catalogue.backends.pycsw_plugin import GeoNodeRepository as CoreGeoNodeRepository


def _text(value):
    return None if value is None else str(value)


class GeoNodeRepository(CoreGeoNodeRepository):
    def query_domain(self, domain, typenames, domainquerytype="list", count=False):
        """Valores de uma propriedade (GetDomain)"""
        objects = self._get_repo_filter(QuerySet(model=ResourceBase))

        if domainquerytype == "range":
            bounds = objects.aggregate(min_value=Min(domain), max_value=Max(domain))
            return [(_text(bounds["min_value"]), _text(bounds["max_value"]))]

        values = objects.exclude(**{f"{domain}__isnull": True}).order_by(domain)
        if count:
            return [
                (_text(row[domain]), row["n"]) for row in values.values(domain).annotate(n=Count("pk")).order_by(domain)
            ]
        return [(_text(value),) for value in values.values_list(domain, flat=True).distinct()]
