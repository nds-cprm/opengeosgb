from django.core.management.base import BaseCommand

from geonode.base.models import ResourceBase

from opengeosgb.signals import GEONODE_DEFAULT_SUPPLEMENTAL_INFORMATION


class Command(BaseCommand):
    help = (
        'Esvazia "informações complementares" dos recursos que ainda têm o texto padrão do GeoNode '
        f'("{GEONODE_DEFAULT_SUPPLEMENTAL_INFORMATION}").'
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Só lista os recursos afetados, sem alterar nada")

    def handle(self, *args, **options):
        qs = ResourceBase.objects.filter(supplemental_information=GEONODE_DEFAULT_SUPPLEMENTAL_INFORMATION)
        total = qs.count()

        if options["dry_run"]:
            for pk, title in qs.values_list("pk", "title"):
                self.stdout.write(f"  {pk}: {title}")
            self.stdout.write(f"{total} recurso(s) seriam alterados (dry-run).")
            return

        # update() não dispara sinais nem regrava o XML de metadados; o XML é atualizado
        # na próxima vez que o recurso for salvo
        updated = qs.update(supplemental_information="")
        self.stdout.write(self.style.SUCCESS(f"{updated} recurso(s) atualizados."))
