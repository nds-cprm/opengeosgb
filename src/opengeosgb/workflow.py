"""
Recalcula as permissões do fluxo de aprovação quando a API v2 muda is_approved, is_published ou o
grupo de um recurso.

No GeoNode 5.0.3, o ResourceBaseSerializer.update (usado por PATCH/PUT em /api/v2/resources/<pk>,
/api/v2/maps/<pk> e /api/v2/documents/<pk>) salva o recurso com save() sem notify=True. Só com
notify=True o ResourceBase.save() compara as flags com was_approved/was_published e chama
set_permissions(approval_status_changed=True). Pela API, as flags são gravadas, mas as permissões
(guardian e regras do GeoFence) continuam as anteriores: um recurso publicado continua invisível
para o anônimo. Ver "Problemas conhecidos" no CLAUDE.md.

O wrapper instalado no ready() (apps.py) lê o estado no banco antes e depois do update original.
Se algo mudou, chama set_permissions com os mesmos argumentos que o save(notify=True) usaria e
sincroniza os campos was_*, para que um save(notify=True) posterior (por exemplo, o
resource_manager.update que a view de datasets chama depois do PATCH) não detecte a mesma mudança
de novo. As notificações de "aprovado"/"publicado" não são enviadas por este caminho.
"""
import functools
import logging

logger = logging.getLogger(__name__)

WORKFLOW_STATE_FIELDS = ("is_approved", "is_published", "group_id")


def get_workflow_state(pk):
    from geonode.base.models import ResourceBase

    if pk is None:
        return None
    return ResourceBase.objects.filter(pk=pk).values(*WORKFLOW_STATE_FIELDS).first()


def sync_workflow_permissions(pk, before):
    """
    Compara o estado salvo com `before` e, se a aprovação, a publicação ou o grupo mudaram,
    recalcula as permissões do fluxo. Devolve True quando recalculou.
    """
    from geonode.base.models import ResourceBase

    after = get_workflow_state(pk)
    if not before or not after:
        return False

    approval_status_changed = any(before[f] != after[f] for f in ("is_approved", "is_published"))
    group_status_changed = before["group_id"] != after["group_id"]
    if not (approval_status_changed or group_status_changed):
        return False

    ResourceBase.objects.filter(pk=pk).update(was_approved=after["is_approved"], was_published=after["is_published"])
    resource = ResourceBase.objects.get(pk=pk).get_real_instance()
    try:
        resource.set_permissions(
            approval_status_changed=approval_status_changed, group_status_changed=group_status_changed
        )
    except Exception:
        # As flags já foram gravadas pelo serializer; falhar aqui devolveria 500 com o recurso
        # alterado. O erro fica no log e o recurso pode ser realinhado pelo admin.
        logger.exception("Falha ao recalcular as permissões do fluxo do recurso %s", pk)
        return False

    logger.info(
        "Permissões do fluxo recalculadas para o recurso %s (aprovação/publicação: %s, grupo: %s)",
        pk,
        approval_status_changed,
        group_status_changed,
    )
    return True


def _wrap_update(original):
    @functools.wraps(original)
    def update(self, instance, validated_data):
        before = get_workflow_state(getattr(instance, "pk", None))
        result = original(self, instance, validated_data)
        sync_workflow_permissions(getattr(result, "pk", None) or instance.pk, before)
        return result

    update._opengeosgb_workflow_sync = True
    return update


def patch_resource_serializer_update():
    """
    Envolve o ResourceBaseSerializer.update do GeoNode. DatasetSerializer, MapSerializer e
    DocumentSerializer herdam o método; o GeoAppSerializer tem update próprio, que já passa pelo
    resource_manager.update(vals=..., notify=True) e recalcula as permissões.
    """
    from geonode.base.api.serializers import ResourceBaseSerializer

    if getattr(ResourceBaseSerializer.update, "_opengeosgb_workflow_sync", False):
        return
    ResourceBaseSerializer.update = _wrap_update(ResourceBaseSerializer.update)
