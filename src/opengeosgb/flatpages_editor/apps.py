from django.apps import AppConfig


class FlatpagesEditorConfig(AppConfig):
    """
    Edição de flatpages com TinyMCE, conteúdo sanitizado e upload de imagens por página.
    Deve vir depois de django.contrib.flatpages no INSTALLED_APPS (substitui o admin dele).
    """

    name = "opengeosgb.flatpages_editor"
    label = "opengeosgb_flatpages"  # "flatpages" já é o rótulo do app do Django
    verbose_name = "Flatpages editor"

    def ready(self):
        from django.contrib.flatpages.models import FlatPage
        from django.db.models.signals import post_delete

        from .signals import flatpage_deleted

        # ao apagar uma flatpage, apaga a pasta de imagens dela (flatpages/<id>/)
        post_delete.connect(flatpage_deleted, sender=FlatPage, dispatch_uid="opengeosgb_flatpage_deleted")
