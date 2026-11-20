"""
Valida o ``metadata_xml`` gravado nos recursos contra o XSD do formato.

    python manage.py validate_metadata_xml [--id 1 --id 2] [--max-errors 5]

Recursos em formato sem XSD configurado (hoje só o ISO 19115-3 tem) são
contados como ignorados. Termina com código 1 se algum XML for inválido.
"""

from django.core.management.base import BaseCommand, CommandError

from geonode.base.models import ResourceBase

from ...formats import format_of_xml
from ...validation import SCHEMA_ROOTS, SchemaNotAvailable, validate_xml


class Command(BaseCommand):
    help = "Valida o XML de metadados dos recursos contra o XSD do formato."

    def add_arguments(self, parser):
        parser.add_argument("--id", action="append", type=int, dest="ids", help="ID do recurso (pode repetir).")
        parser.add_argument("--max-errors", type=int, default=5, help="Erros mostrados por recurso (padrão: 5).")

    def handle(self, *args, **options):
        resources = ResourceBase.objects.non_polymorphic().exclude(metadata_xml__isnull=True).exclude(metadata_xml="")
        if options["ids"]:
            resources = resources.filter(id__in=options["ids"])

        valid = invalid = skipped = 0
        for resource in resources.only("id", "title", "metadata_xml").order_by("id").iterator():
            fmt = format_of_xml(resource.metadata_xml)
            if fmt not in SCHEMA_ROOTS:
                skipped += 1
                continue
            try:
                errors = validate_xml(resource.metadata_xml, fmt)
            except SchemaNotAvailable as err:
                raise CommandError(str(err))
            if not errors:
                valid += 1
                continue
            invalid += 1
            self.stdout.write(self.style.ERROR(f"[{resource.id}] {resource.title}: {len(errors)} erro(s)"))
            for error in errors[: options["max_errors"]]:
                self.stdout.write(f"    {error}")

        self.stdout.write(f"válidos: {valid}  inválidos: {invalid}  ignorados (sem XSD): {skipped}")
        if invalid:
            raise SystemExit(1)
