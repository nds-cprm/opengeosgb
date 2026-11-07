"""
Aprovação e publicação de recursos pelo admin do Django.

Enquanto as caixas "Publicado" e "Aprovado" não aparecem no painel do client (ver "Problemas
conhecidos" no CLAUDE.md), o admin é o lugar dessas mudanças. Os admins do GeoNode salvam com
ResourceBase.save(notify=False), que só grava os campos; aqui, quando is_approved/is_published
mudam, o recurso é salvo com notify=True, que também atualiza as permissões do fluxo de aprovação
(e as regras no GeoServer) e envia as notificações, como na API.
"""
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from geonode.documents.admin import DocumentAdmin
from geonode.documents.models import Document
from geonode.geoapps.admin import GeoAppAdmin
from geonode.geoapps.models import GeoApp
from geonode.layers.admin import DatasetAdmin
from geonode.layers.models import Dataset
from geonode.maps.admin import MapAdmin
from geonode.maps.models import Map

WORKFLOW_FIELDS = ("is_approved", "is_published")


def save_with_workflow(resource, **values):
    """
    Aplica os valores e salva com notify=True. Os campos was_* recebem o estado atual do banco,
    para que ResourceBase.save() detecte a mudança mesmo se estiverem dessincronizados.
    """
    current = type(resource).objects.filter(pk=resource.pk).values(*WORKFLOW_FIELDS).first()
    if current:
        resource.was_approved = current["is_approved"]
        resource.was_published = current["is_published"]
    for field, value in values.items():
        setattr(resource, field, value)
    resource.save(notify=True)


class WorkflowAdminMixin:
    actions = ("approve", "publish", "approve_and_publish", "unpublish", "unapprove")

    def save_model(self, request, obj, form, change):
        if change and set(WORKFLOW_FIELDS) & set(form.changed_data):
            save_with_workflow(obj)
        else:
            super().save_model(request, obj, form, change)

    def _apply(self, request, queryset, values):
        changed = 0
        for resource in queryset:
            if any(getattr(resource, field) != value for field, value in values.items()):
                save_with_workflow(resource, **values)
                changed += 1
        self.message_user(
            request,
            ngettext("%(count)d resource updated.", "%(count)d resources updated.", changed) % {"count": changed},
            messages.SUCCESS,
        )

    @admin.action(description=_("Approve selected resources"), permissions=["change"])
    def approve(self, request, queryset):
        self._apply(request, queryset, {"is_approved": True})

    @admin.action(description=_("Publish selected resources"), permissions=["change"])
    def publish(self, request, queryset):
        self._apply(request, queryset, {"is_published": True})

    @admin.action(description=_("Approve and publish selected resources"), permissions=["change"])
    def approve_and_publish(self, request, queryset):
        self._apply(request, queryset, {"is_approved": True, "is_published": True})

    @admin.action(description=_("Unpublish selected resources"), permissions=["change"])
    def unpublish(self, request, queryset):
        self._apply(request, queryset, {"is_published": False})

    @admin.action(description=_("Unapprove selected resources"), permissions=["change"])
    def unapprove(self, request, queryset):
        self._apply(request, queryset, {"is_approved": False})


class WorkflowDatasetAdmin(WorkflowAdminMixin, DatasetAdmin):
    pass


class WorkflowMapAdmin(WorkflowAdminMixin, MapAdmin):
    pass


class WorkflowDocumentAdmin(WorkflowAdminMixin, DocumentAdmin):
    pass


class WorkflowGeoAppAdmin(WorkflowAdminMixin, GeoAppAdmin):
    pass


# substitui os admins do GeoNode (o app opengeosgb é carregado depois dos apps do GeoNode)
for model, model_admin in (
    (Dataset, WorkflowDatasetAdmin),
    (Map, WorkflowMapAdmin),
    (Document, WorkflowDocumentAdmin),
    (GeoApp, WorkflowGeoAppAdmin),
):
    if admin.site.is_registered(model):
        admin.site.unregister(model)
    admin.site.register(model, model_admin)
