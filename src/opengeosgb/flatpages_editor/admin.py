from django.contrib import admin
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage
from tinymce.widgets import TinyMCE

from .editor import TINYMCE_CONFIG, move_temp_images, sanitize_html


class TinyMCEFlatpageForm(FlatpageForm):
    """Conteúdo editado com TinyMCE e sanitizado ao salvar (ver editor.py)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # páginas já salvas enviam as imagens direto para a pasta delas (flatpages/<id>/)
        upload_url = str(TINYMCE_CONFIG["images_upload_url"])
        if self.instance.pk:
            upload_url += f"?page={self.instance.pk}"
        self.fields["content"].widget = TinyMCE(mce_attrs={**TINYMCE_CONFIG, "images_upload_url": upload_url})

    def clean_content(self):
        return sanitize_html(self.cleaned_data.get("content", ""))


class TinyMCEFlatPageAdmin(FlatPageAdmin):
    form = TinyMCEFlatpageForm

    class Media:
        # o nome do arquivo não pode terminar em "tinymce.js": o TinyMCE usaria a pasta dele
        # como base para carregar temas, ícones e traduções
        js = ("flatpages_editor/js/image_upload.js",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # imagens enviadas antes de a página existir: mover para flatpages/<id>/
        if move_temp_images(obj):
            FlatPage.objects.filter(pk=obj.pk).update(content=obj.content)


# substitui o admin de django.contrib.flatpages (este app é carregado depois dele)
if admin.site.is_registered(FlatPage):
    admin.site.unregister(FlatPage)
admin.site.register(FlatPage, TinyMCEFlatPageAdmin)
