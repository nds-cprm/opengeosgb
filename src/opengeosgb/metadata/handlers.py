from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import pgettext

from geonode.metadata.handlers.abstract import MetadataHandler
from geonode.metadata.handlers.base import BaseHandler
from geonode.metadata.handlers.region import RegionHandler
from geonode.metadata.models import SparseField

from .fields import SPARSE_FIELDS
from .i18n import normalize_text, region_label

# Campos do editor cujas opções (oneOf) o GeoNode monta sem gettext, e o contexto
# (msgctxt) usado para traduzi-las no django.po do opengeosgb.
OPTION_CONTEXTS = {
    "language": "metadata language",
    "restriction_code_type": "metadata restriction code",
    "spatial_representation_type": "metadata spatial representation type",
}

# Campos cujas opções são reordenadas pelo título já traduzido
SORTED_FIELDS = {"language"}


class OptionsI18nHandler(MetadataHandler):
    """
    Traduz títulos e descrições das opções de campos do editor de metadados.

    Não é dono de nenhum campo: apenas ajusta o schema montado pelos handlers do
    GeoNode, por isso deve ser registrado depois deles (ver apps.py).
    """

    def update_schema(self, jsonschema, context, lang=None):
        for field, msgctxt in OPTION_CONTEXTS.items():
            options = jsonschema["properties"].get(field, {}).get("oneOf")
            if not options:
                continue

            for option in options:
                for attr in ("title", "description"):
                    if option.get(attr):
                        option[attr] = pgettext(msgctxt, option[attr])

            if field in SORTED_FIELDS:
                options.sort(key=lambda option: normalize_text(option["title"]))

        return jsonschema

    def get_jsonschema_instance(self, resource, field_name, context, errors, lang=None):
        return None

    def update_resource(self, resource, field_name, json_instance, context, errors, **kwargs):
        pass


class SparseFieldsUiHandler(MetadataHandler):
    """
    Complementa os campos esparsos do opengeosgb (fields.py), que são gravados pelo
    SparseHandler do GeoNode: liga o autocomplete de cada campo e, ao salvar, remove os
    campos de objeto deixados vazios (o GeoNode os grava como "{}").
    Deve ser registrado depois do handler "sparse".
    """

    def update_schema(self, jsonschema, context, lang=None):
        for field_name, info in SPARSE_FIELDS.items():
            subschema = jsonschema["properties"].get(field_name)
            if subschema is not None and info.get("autocomplete"):
                subschema.setdefault("ui:options", {})["geonode-ui:autocomplete"] = reverse(info["autocomplete"])
        return jsonschema

    def get_jsonschema_instance(self, resource, field_name, context, errors, lang=None):
        return None

    def update_resource(self, resource, field_name, json_instance, context, errors, **kwargs):
        pass

    def post_save(self, resource, json_instance, context, errors, **kwargs):
        empty = [
            name
            for name, info in SPARSE_FIELDS.items()
            if info["schema"]["type"] == "object" and not json_instance.get(name)
        ]
        if empty:
            # só apaga registros vazios: em atualizações parciais o campo pode nem ter sido enviado
            SparseField.objects.filter(resource=resource, name__in=empty, value__in=["{}", "null", ""]).delete()


class BaseFormHandler(BaseHandler):
    """
    Handler base do GeoNode com ajustes do formulário do opengeosgb:

    - "date" é editado só como data (sem hora); ao salvar, o horário já gravado é mantido;
    - "supplemental_information" não tem texto padrão (no GeoNode é "No information provided"),
      e o valor nulo vindo do editor é gravado como texto vazio (a coluna é NOT NULL).
    """

    def update_schema(self, jsonschema, context, lang=None):
        jsonschema = super().update_schema(jsonschema, context, lang)
        properties = jsonschema["properties"]
        properties["date"]["format"] = "date"
        properties["supplemental_information"].pop("default", None)
        return jsonschema

    def get_jsonschema_instance(self, resource, field_name, context, errors, lang=None):
        if field_name == "date" and isinstance(resource.date, datetime):
            return timezone.localtime(resource.date).date().isoformat()
        return super().get_jsonschema_instance(resource, field_name, context, errors, lang)

    def update_resource(self, resource, field_name, json_instance, context, errors, **kwargs):
        if field_name == "supplemental_information" and json_instance.get(field_name) is None:
            json_instance = {**json_instance, field_name: ""}
            return super().update_resource(resource, field_name, json_instance, context, errors, **kwargs)

        value = json_instance.get(field_name) if field_name == "date" else None
        new_date = parse_date(value) if isinstance(value, str) else None
        if not new_date:
            # outros campos, ou data vinda com hora: comportamento original
            return super().update_resource(resource, field_name, json_instance, context, errors, **kwargs)

        current_time = timezone.localtime(resource.date).time() if resource.date else datetime.min.time()
        resource.date = timezone.make_aware(datetime.combine(new_date, current_time))
        context.setdefault("base", {})[field_name] = resource.date


class RegionsI18nHandler(RegionHandler):
    """
    Handler de regiões com nomes traduzidos: usa o autocomplete do opengeosgb e
    traduz os rótulos das regiões já associadas ao recurso.
    """

    def update_schema(self, jsonschema, context, lang=None):
        jsonschema = super().update_schema(jsonschema, context, lang)
        jsonschema["properties"]["regions"]["ui:options"]["geonode-ui:autocomplete"] = reverse(
            "opengeosgb_metadata_autocomplete_regions"
        )
        return jsonschema

    def get_jsonschema_instance(self, resource, field_name, context, errors, lang=None):
        return [{"id": str(r.id), "label": region_label(r)} for r in resource.regions.all()]
