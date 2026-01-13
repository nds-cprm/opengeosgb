from django.contrib import admin
from django.contrib.flatpages.models import FlatPage
from django.contrib.flatpages.admin import FlatPageAdmin
from tinymce.widgets import TinyMCE


class GrappelliFlatPageAdmin(FlatPageAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'content':
            # O Grappelli renderizará o widget TinyMCE com seu próprio estilo
            return db_field.formfield(widget=TinyMCE(
                attrs={'cols': 80, 'rows': 30},
                mce_attrs={'external_config': '/static/js/tinymce_setup.js'} # Opcional: setup do Grappelli
            ))
        return super().formfield_for_dbfield(db_field, **kwargs)

admin.site.unregister(FlatPage)
admin.site.register(FlatPage, GrappelliFlatPageAdmin)
