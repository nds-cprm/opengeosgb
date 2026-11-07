# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2018 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################
import os
from django.apps import AppConfig as BaseAppConfig


def run_setup_hooks(*args, **kwargs):
    from django.conf import settings
    from .celeryapp import app as celeryapp

    LOCAL_ROOT = os.path.abspath(os.path.dirname(__file__))
    settings.TEMPLATES[0]["DIRS"].insert(0, os.path.join(LOCAL_ROOT, "templates"))

    if celeryapp not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS += (celeryapp,)

    # Tradução das opções do editor de metadados; registrado por último para rodar
    # depois dos handlers do GeoNode
    from geonode.metadata.manager import metadata_manager
    from .metadata.handlers import BaseFormHandler, OptionsI18nHandler, RegionsI18nHandler, SparseFieldsUiHandler

    metadata_manager.add_handler("opengeosgb_i18n", OptionsI18nHandler)
    metadata_manager.add_handler("opengeosgb_sparse_ui", SparseFieldsUiHandler)
    # substituem os handlers do GeoNode (mantêm a mesma posição na ordem)
    metadata_manager.add_handler("base", BaseFormHandler)
    metadata_manager.add_handler("region", RegionsI18nHandler)

    # Campos extras do editor de metadados (campos esparsos)
    from geonode.metadata.handlers.sparse import sparse_field_registry
    from .metadata.fields import SPARSE_FIELDS

    for field_name, info in SPARSE_FIELDS.items():
        sparse_field_registry.register(field_name, info["schema"], after=info["after"])

    # Escala na API de recursos (campo diferido) e no preset do painel de propriedades do client
    # (viewer_common, definido no ready() do geonode_mapstore_client, que é carregado antes)
    from .metadata.fields import SCALE_FIELD
    from .metadata.serializers import add_sparse_fields_to_api

    add_sparse_fields_to_api()
    viewer_common = settings.REST_API_PRESETS.get("viewer_common", {}).get("include[]")
    if isinstance(viewer_common, list) and SCALE_FIELD not in viewer_common:
        viewer_common.append(SCALE_FIELD)

    # Filtro por escala na API de recursos (?scale=<denominador>), usado pela barra de filtros do
    # catálogo; a API de facets usa os filtros do ResourceBaseViewSet para as contagens
    from geonode.base.api.views import ResourceBaseViewSet
    from .metadata.facets import ScaleFilter

    if ScaleFilter not in ResourceBaseViewSet.filter_backends:
        ResourceBaseViewSet.filter_backends = list(ResourceBaseViewSet.filter_backends) + [ScaleFilter]

    # Padrões do opengeosgb na criação de recursos (informações complementares)
    from django.db.models.signals import pre_save
    from .signals import set_resource_defaults

    pre_save.connect(set_resource_defaults, dispatch_uid="opengeosgb_set_resource_defaults")


class AppConfig(BaseAppConfig):
    name = "opengeosgb"
    label = "opengeosgb"

    def ready(self):
        super(AppConfig, self).ready()
        run_setup_hooks()
