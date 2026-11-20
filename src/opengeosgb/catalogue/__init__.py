"""
App ``opengeosgb.catalogue``: sobrescreve o catálogo (CSW/pycsw) do GeoNode 5.0.x
sem mudar o núcleo.

- formato de metadados configurável (ISO 19139 ou ISO 19115-3), em ``formats``;
- backend ``opengeosgb.catalogue.backends.pycsw_local`` (``CATALOGUE_ENGINE``);
- view própria do endpoint ``/catalogue/csw`` (``views``);
- templates XML do projeto (``templates/opengeosgb_catalogue/``).
"""
