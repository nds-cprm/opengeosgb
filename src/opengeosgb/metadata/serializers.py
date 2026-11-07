"""
Campos esparsos do opengeosgb expostos na API de recursos (/api/v2/resources, /api/v2/datasets...).

Os serializers do GeoNode não trazem campos esparsos (tabela SparseField). Aqui o campo "scale" é
acrescentado aos serializers de recursos em tempo de execução (ver apps.py), como campo diferido:
só é calculado quando pedido explicitamente (include[]=scale ou um preset que o inclua, como o
viewer_common usado pelo painel de propriedades do client), evitando uma consulta por recurso nas
listagens.
"""
import json

from dynamic_rest.fields.fields import DynamicField

from geonode.metadata.models import SparseField

from .fields import SCALE_FIELD


class SparseObjectField(DynamicField):
    """Lê um campo esparso de objeto ({"id", "label"}) do recurso; None se não existir ou estiver vazio."""

    def __init__(self, sparse_name, **kwargs):
        self.sparse_name = sparse_name
        kwargs.setdefault("source", "*")
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, instance):
        value = (
            SparseField.objects.filter(resource_id=instance.pk, name=self.sparse_name)
            .values_list("value", flat=True)
            .first()
        )
        try:
            data = json.loads(value) if value else None
        except ValueError:
            return None
        return data if isinstance(data, dict) and data.get("id") else None


def add_sparse_fields_to_api():
    """Acrescenta o campo "scale" (diferido) aos serializers de recursos do GeoNode."""
    from geonode.base.api.serializers import ResourceBaseSerializer
    from geonode.documents.api.serializers import DocumentSerializer
    from geonode.geoapps.api.serializers import GeoAppSerializer
    from geonode.layers.api.serializers import DatasetSerializer
    from geonode.maps.api.serializers import MapSerializer

    for serializer in (ResourceBaseSerializer, DatasetSerializer, MapSerializer, DocumentSerializer, GeoAppSerializer):
        if SCALE_FIELD in serializer._declared_fields:
            continue
        serializer._declared_fields[SCALE_FIELD] = SparseObjectField(SCALE_FIELD, deferred=True)
        fields = serializer.Meta.fields
        if fields != "__all__" and SCALE_FIELD not in fields:
            serializer.Meta.fields = (
                tuple(fields) + (SCALE_FIELD,) if isinstance(fields, tuple) else list(fields) + [SCALE_FIELD]
            )
