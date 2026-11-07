# Campos extras do editor de metadados, gravados como campos esparsos do GeoNode
# (tabela SparseField) e registrados no ready() do app (ver apps.py).
# Títulos e descrições em português ficam no tesauro labels-i18n (<campo>__ovr, <campo>__descr__ovr).

SCALE_FIELD = "scale"

# Seleção única com autocomplete: o editor do GeoNode só oferece autocomplete para
# objetos {id, label} (ou listas), por isso a escala é um objeto e não um inteiro.
SCALE_SCHEMA = {
    "type": "object",
    "title": "Scale",
    "description": "Choose a scale from the list or type its denominator (e.g. 250000 or 1:250,000)",
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "label": {"type": "string"},
    },
}

# Escalas sugeridas no autocomplete (denominadores), além das já usadas em outros recursos
COMMON_SCALES = [
    1000, 2000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000, 2500000, 5000000,
]

# nome -> schema, campo após o qual aparece no formulário e rota do autocomplete (se houver)
SPARSE_FIELDS = {
    SCALE_FIELD: {
        "schema": SCALE_SCHEMA,
        "after": "spatial_representation_type",
        "autocomplete": "opengeosgb_metadata_autocomplete_scales",
    },
}
