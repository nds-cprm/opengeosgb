from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Warning, register


class CatalogueConfig(AppConfig):
    name = "opengeosgb.catalogue"
    label = "opengeosgb_catalogue"
    verbose_name = "OpenGeoSGB - Catálogo (CSW)"

    def ready(self):
        from django.db.models.signals import pre_save

        from .formats import default_format
        from .signals import sync_csw_format

        default_format()  # valida CATALOGUE_DEFAULT_FORMAT na inicialização
        pre_save.connect(sync_csw_format, dispatch_uid="opengeosgb_catalogue_sync_csw_format")


ENGINE = "opengeosgb.catalogue.backends.pycsw_local"


@register()
def check_catalogue_settings(app_configs, **kwargs):
    from .formats import METADATA_TEMPLATES, default_format

    messages = []
    engine = settings.CATALOGUE["default"]["ENGINE"]
    if engine != ENGINE:
        messages.append(
            Warning(
                f"CATALOGUE['default']['ENGINE'] é {engine!r}: o formato {default_format()!r} e os perfis "
                "do opengeosgb.catalogue não valem para o catalogue_post_save.",
                hint=f"Use CATALOGUE_ENGINE={ENGINE}.",
                id="opengeosgb_catalogue.W001",
            )
        )
    expected = METADATA_TEMPLATES[default_format()]
    if settings.CATALOG_METADATA_TEMPLATE != expected:
        messages.append(
            Warning(
                f"CATALOG_METADATA_TEMPLATE ({settings.CATALOG_METADATA_TEMPLATE!r}) não é o template padrão do "
                f"formato {default_format()!r} ({expected!r}). O XML precisa ter a raiz desse formato.",
                id="opengeosgb_catalogue.W002",
            )
        )
    return messages
