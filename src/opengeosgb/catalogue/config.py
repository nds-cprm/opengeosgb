"""
Configuração do pycsw usada pelo backend e pela view do opengeosgb.

No GeoNode 5.0.x a configuração é montada com ``dict(settings, **CONFIGURATION)``:
- a cópia é rasa, então ``repository`` é o próprio dicionário do módulo
  ``pycsw_local`` e a view do núcleo altera o filtro dele in-place, um estado
  compartilhado entre requisições;
- os padrões do módulo vencem os settings, inclusive em ``profiles``, o que
  impede ligar o perfil ``iso19115p3`` pelos settings.

Aqui cada chamada devolve um dicionário novo, mesclado em profundidade, com os
settings vencendo os padrões e os perfis necessários para os formatos do
projeto.
"""

import copy

from django.conf import settings

from geonode.catalogue.backends.pycsw_local import CONFIGURATION as CORE_CONFIGURATION

from .constants import PYCSW_PROFILES

CORE_REPOSITORY = "geonode.catalogue.backends.pycsw_plugin.GeoNodeRepository"
REPOSITORY = "opengeosgb.catalogue.backends.pycsw_repository.GeoNodeRepository"


def _deep_merge(base, override):
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def build_pycsw_config():
    config = _deep_merge(copy.deepcopy(CORE_CONFIGURATION), copy.deepcopy(settings.PYCSW["CONFIGURATION"]))
    profiles = config.get("profiles") or ()
    if isinstance(profiles, str):
        profiles = [p.strip() for p in profiles.split(",") if p.strip()]
    config["profiles"] = set(profiles) | PYCSW_PROFILES
    # repositório com o GetDomain corrigido, a não ser que os settings indiquem outro
    if config["repository"].get("source") == CORE_REPOSITORY:
        config["repository"]["source"] = REPOSITORY
    return config
