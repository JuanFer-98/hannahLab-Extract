from io import BytesIO
from types import ModuleType

import pdfplumber

import PRODUCTOS.prelosas as prelosas

DISPLAY_NAMES: dict[str, list[str]] = {
    "PRELOSAS": [
        "Aligerada 1D 25cm (A=15) (T) (C=38)",
        "Aligerada 2D 25cm",
        "Maciza 25cm",
        "Maciza 30cm (T) (C=38)",
        "Maciza 30cm Postensada",
        "Aligerada 1D 25cm Postensada",
    ],
    "PREVIGAS": [
        "Vigas H <= 0.70m (C=35)",
        "Vigas 0.70m < H <= 1.20m",
        "Vigas 1.20m < H <= 2.00m",
        "Viga E1-ANG",
        "Viga E2-ANG",
        "Viga E3-ANG",
    ],
    "FRISOS": [
        "Friso H=20cm (e=15)",
        "Friso H=30cm",
        "Friso H=50cm",
        "Friso E1-ANG",
    ],
    "COLGAJOS": [
        "Colgajo H=20cm (e=12)",
        "Colgajo H=30cm",
        "Colgajo E1-ANG",
    ],
    "MUROS WC": [
        "Muros WC (C=38)",
    ],
    "MUROS ALVEOLARES": [
        "Muro Alveolar e=20cm",
        "Muro Alveolar e=30cm",
    ],
    "MUROS DOPPEL": [
        "Muro Doppel e=20cm",
        "Muro Doppel e=30cm",
    ],
    "MUROS SOLIDOS": [
        "Muro Sólido e=20cm",
        "Muro Sólido e=30cm",
    ],
    "MUROS NEW JERSEY": [
        "New Jersey T1-ANG",
        "New Jersey T2-ANG",
    ],
    "ESPECIALES (FACHADA)": [
        "Fachada E1-ANG",
        "Fachada E2-ANG",
    ],
    "ESPECIALES (COLUMNETAS)": [
        "Columneta T1-ANG",
        "Columneta T2-ANG",
    ],
    "ESPECIALES (PRELOSAS)": [
        "Maciza Especial e=7cm-ANG",
    ],
    "ESCALERAS COMPLETAS": [
        "Escalera Tipo I-ANG",
        "Escalera Tipo 12-ANG",
        "Escalera Tipo A-ANG",
    ],
}

# Cada handler es un módulo de PRODUCTOS/ que expone:
#   extract_divisiones(text, tables) -> dict
#   extract_subtotales_disgregados(text, tables) -> dict[str, str]
#   calcular_total(subtotales) -> str
PRODUCT_HANDLERS: dict[str, ModuleType] = {
    "PRELOSAS": prelosas,
    # "PREVIGAS": previgas,
    # "FRISOS":   frisos,
    # ... agrega aquí cada nuevo producto
}


def extract_text_and_tables(file_bytes: bytes) -> tuple[str, list[list[list[str]]]]:
    text_parts: list[str] = []
    tables: list[list[list[str]]] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
            for table in page.extract_tables() or []:
                tables.append(table)
    extract = "\n".join(text_parts)
    print(f"Total tablas extraídas: {len(tables)}")
    return extract, tables


def process_pdf(file_bytes: bytes, product: str) -> dict:
    if product not in DISPLAY_NAMES:
        raise ValueError(f"Producto desconocido: '{product}'. Válidos: {list(DISPLAY_NAMES)}")

    print(f"Processing PDF for product: {product}")
    text, tables = extract_text_and_tables(file_bytes)

    entry: dict = {}
    handler = PRODUCT_HANDLERS.get(product)
    if handler is not None:
        if len(tables) > 1:
            entry["Divisiones"] = handler.extract_divisiones(text, tables)
        entry["subtotales_disgregados"] = handler.extract_subtotales_disgregados(text, tables)
        entry["total"] = handler.calcular_total(entry["subtotales_disgregados"])

    return {product: [entry]}
