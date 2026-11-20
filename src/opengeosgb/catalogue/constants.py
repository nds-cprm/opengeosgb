"""Constantes do catálogo, sem dependências: podem ser importadas nos settings."""

ISO19139 = "ISO"
ISO19115_3 = "ISO19115-3_2018"

# formatos que podem ser gravados em metadata_xml -> template padrão
METADATA_TEMPLATES = {
    ISO19139: "opengeosgb_catalogue/full_metadata_iso19139.xml",
    ISO19115_3: "opengeosgb_catalogue/full_metadata_iso19115-3.xml",
}

# perfis do pycsw necessários para ler e devolver cada formato
PYCSW_PROFILES = {"apiso", "ebrim", "iso19115p3"}
