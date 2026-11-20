"""
Atualiza a cópia local dos XSD usados na validação dos metadados
(``opengeosgb/catalogue/schemas/``).

Baixa o schema raiz de cada formato e, recursivamente, todos os ``xs:import``,
``xs:include`` e ``xs:redefine``. Os arquivos são gravados espelhando
``host/caminho`` da URL, com os ``schemaLocation`` reescritos como caminhos
relativos, para que a validação funcione sem rede.

    python manage.py fetch_metadata_schemas [--cache DIR]
"""

import os
import pathlib
import shutil
import tempfile
import time
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from lxml import etree

from ...validation import SCHEMA_ROOTS, SCHEMAS_DIR

XS = "{http://www.w3.org/2001/XMLSchema}"
REFERENCES = (XS + "import", XS + "include", XS + "redefine")


def _local_path(base, url):
    parsed = urllib.parse.urlparse(url)
    return base / parsed.netloc / parsed.path.lstrip("/")


def _parse(data):
    return etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))


class Command(BaseCommand):
    help = "Baixa os XSD dos formatos de metadados para opengeosgb/catalogue/schemas/."

    def add_arguments(self, parser):
        parser.add_argument("--cache", help="Diretório para guardar os arquivos originais e reaproveitá-los.")
        parser.add_argument("--retries", type=int, default=3)

    def _download(self, url, dest, retries):
        for attempt in range(1, retries + 1):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "opengeosgb-fetch-metadata-schemas"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = response.read()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                return
            except OSError as err:
                if attempt == retries:
                    raise CommandError(f"Falha ao baixar {url}: {err}")
                time.sleep(2 * attempt)

    def handle(self, *args, **options):
        cache = pathlib.Path(options["cache"] or tempfile.mkdtemp(prefix="opengeosgb-xsd-"))
        out = pathlib.Path(tempfile.mkdtemp(prefix="opengeosgb-xsd-out-"))

        seen = set()
        todo = [url for url in SCHEMA_ROOTS.values()]
        while todo:
            url = todo.pop()
            if url in seen:
                continue
            seen.add(url)

            raw = _local_path(cache, url)
            if not raw.exists():
                self.stdout.write(f"baixando {url}")
                self._download(url, raw, options["retries"])

            doc = _parse(raw.read_bytes())
            target = _local_path(out, url)
            for el in doc.iter(*REFERENCES):
                location = el.get("schemaLocation")
                if not location:
                    continue
                ref_url = urllib.parse.urljoin(url, location)
                todo.append(ref_url)
                el.set("schemaLocation", os.path.relpath(_local_path(out, ref_url), target.parent))

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(etree.tostring(doc, xml_declaration=True, encoding="UTF-8"))

        (out / "README.md").write_text(
            "Cópia local dos XSD usados por `opengeosgb.catalogue.validation`.\n\n"
            "Gerada por `python manage.py fetch_metadata_schemas`; não edite à mão. Os arquivos espelham\n"
            "`host/caminho` das URLs originais, com os `schemaLocation` reescritos como caminhos relativos.\n\n"
            "Raízes:\n\n" + "".join(f"- {fmt}: {url}\n" for fmt, url in SCHEMA_ROOTS.items())
        )

        if SCHEMAS_DIR.exists():
            shutil.rmtree(SCHEMAS_DIR)
        shutil.copytree(out, SCHEMAS_DIR)
        shutil.rmtree(out)
        self.stdout.write(self.style.SUCCESS(f"{len(seen)} schemas gravados em {SCHEMAS_DIR}"))
