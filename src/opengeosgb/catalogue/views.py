"""
Endpoint ``/catalogue/csw`` do opengeosgb.

Versão própria de ``geonode.catalogue.views.csw_global_dispatch`` (GeoNode
5.0.x). Não dá para só envolver a view do núcleo, porque ela redireciona quando
``CATALOGUE["default"]["ENGINE"]`` não é exatamente
``geonode.catalogue.backends.pycsw_local``.

Diferenças em relação ao núcleo:
- a configuração do pycsw é nova a cada requisição (``build_pycsw_config``),
  sem o estado compartilhado do dicionário ``repository`` entre threads, e já
  traz o perfil ``iso19115p3``;
- as cláusulas do filtro são combinadas só com ``AND``. No núcleo, o usuário
  autenticado recebe ``(...) OR (id IN ...)``, e os filtros de
  ``ALTERNATES_ONLY`` e ``GROUP_PRIVATE_RESOURCES`` acrescentados depois deixam
  de valer para ele;
- o conjunto autorizado passa por ``dataset_filter`` (por padrão
  ``filters.csw_dataset_filter``).

Ao atualizar o GeoNode, compare com ``geonode/catalogue/views.py``.
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from guardian.shortcuts import get_objects_for_user
from pycsw import server

import geonode.catalogue.views as core_views
from geonode.base.auth import get_or_create_token
from geonode.groups.models import GroupProfile

from .config import build_pycsw_config
from .filters import csw_dataset_filter

LOCAL_ENGINES = (
    "opengeosgb.catalogue.backends.pycsw_local",
    "geonode.catalogue.backends.pycsw_local",
)


def _authorized_ids(request, dataset_filter):
    """IDs dos recursos que o usuário pode ver, depois do ``dataset_filter``."""
    username = str(request.user) if request.user else "AnonymousUser"
    profile = get_user_model().objects.filter(username=username).first()
    if profile is None:
        return []
    resources = get_objects_for_user(profile, "base.view_resourcebase")
    if dataset_filter:
        resources = dataset_filter(resources)
    return list(resources.values_list("id", flat=True))


def _group_ids(request):
    """Grupos do usuário mais os grupos não privados (GROUP_PRIVATE_RESOURCES)."""
    groups_ids = []
    if request.user and request.user.is_authenticated:
        groups_ids.extend(request.user.groups.values_list("id", flat=True))
        try:
            groups_ids.extend(g["group"] for g in request.user.group_list_all().values("group") if "group" in g)
        except Exception:
            pass
    groups_ids.extend(GroupProfile.objects.exclude(access="private").values_list("group", flat=True))
    return sorted({g for g in groups_ids if g is not None})


def _repository_filter(request, base_filter, dataset_filter):
    clauses = [base_filter] if base_filter else []

    authorized_ids = _authorized_ids(request, dataset_filter)
    if authorized_ids:
        clauses.append(f"id IN ({', '.join(str(i) for i in authorized_ids)})")
    else:
        clauses.append("id = -9999")

    if settings.CATALOGUE["default"].get("ALTERNATES_ONLY"):
        clauses.append("alternate IS NOT NULL")

    is_admin = bool(request.user and request.user.is_superuser)
    if not is_admin and settings.GROUP_PRIVATE_RESOURCES:
        groups_ids = _group_ids(request)
        if groups_ids:
            clauses.append(f"(group_id IS NULL OR group_id IN ({', '.join(str(g) for g in groups_ids)}))")
        else:
            clauses.append("group_id IS NULL")

    return " AND ".join(f"({c})" for c in clauses)


@csrf_exempt
def csw_global_dispatch(request, dataset_filter=csw_dataset_filter):
    """pycsw wrapper"""
    if settings.CATALOGUE["default"]["ENGINE"] not in LOCAL_ENGINES:
        return HttpResponseRedirect(settings.CATALOGUE["default"]["URL"])

    mdict = build_pycsw_config()

    access_token = None
    if request and request.user:
        access_token = get_or_create_token(request.user)
        if access_token and access_token.is_expired():
            access_token = None

    absolute_uri = f"{request.build_absolute_uri()}"
    query_string = f"{request.META['QUERY_STRING']}"
    env = request.META.copy()

    if access_token:
        env.update({"access_token": access_token.token})
        if "access_token" not in query_string:
            absolute_uri = f"{absolute_uri}&access_token={access_token.token}"
            query_string = f"{query_string}&access_token={access_token.token}"

    env.update(
        {
            # a raiz da app do núcleo, onde o pycsw procura os recursos estáticos
            "local.app_root": os.path.dirname(core_views.__file__),
            "REQUEST_URI": absolute_uri,
            "QUERY_STRING": query_string,
        }
    )

    mdict["repository"]["filter"] = _repository_filter(request, mdict["repository"].get("filter"), dataset_filter)

    csw = server.Csw(mdict, env, version="2.0.2")
    content = csw.dispatch_wsgi()

    # pycsw >= 2.0: [http_status_code, content]
    if isinstance(content, list):
        content = content[1]

    return HttpResponse(content, content_type=csw.contenttype)
