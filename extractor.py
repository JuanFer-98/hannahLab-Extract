from io import BytesIO

import pdfplumber

PRODUCT_NAMES = [
    "PRELOSAS",
    "PREVIGAS",
    "FRISOS",
    "COLGAJOS",
    "MUROS WC",
    "MUROS ALVEOLARES",
    "MUROS DOPPEL",
    "MUROS SOLIDOS",
    "MUROS NEW JERSEY",
    "ESPECIALES (FACHADA)",
    "ESPECIALES (COLUMNETAS)",
    "ESPECIALES (PRELOSAS)",
    "ESCALERAS COMPLETAS",
]

DISPLAY_NAMES = {
    "PRELOSAS": "Prelosa",
    "PREVIGAS": "Previga",
    "FRISOS": "Friso",
    "COLGAJOS": "Colgajo",
    "MUROS WC": "Muro WC",
    "MUROS ALVEOLARES": "Muro Alveolar",
    "MUROS DOPPEL": "Muro Doppel",
    "MUROS SOLIDOS": "Muro Solido",
    "MUROS NEW JERSEY": "Muro New Jersey",
    "ESPECIALES (FACHADA)": "Especial Fachada",
    "ESPECIALES (COLUMNETAS)": "Especial Columneta",
    "ESPECIALES (PRELOSAS)": "Especial Prelosa",
    "ESCALERAS COMPLETAS": "Escalera Completa",
}


def extract_text_and_tables(file_bytes: bytes) -> tuple[str, list[list[list[str]]]]:
    text_parts: list[str] = []
    tables: list[list[list[str]]] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
            for table in page.extract_tables() or []:
                tables.append(table)
    return "\n".join(text_parts), tables


def product_extract(text: str) -> list[str]:
    text_upper = text.upper()
    work = text_upper
    found: set[str] = set()
    for name in sorted(PRODUCT_NAMES, key=len, reverse=True):
        if name in work:
            found.add(name)
            work = work.replace(name, " " * len(name))
    return [name for name in PRODUCT_NAMES if name in found]


def extract_divisiones(text: str, tables: list[list[list[str]]], producto: str) -> dict:
    """
    Construye el dict de divisiones para un producto.

    Forma esperada (stub — se irá completando con reglas que el usuario provea):
    {
      "TORRE1": {
        "CISTERNA": {"ALIGERADA 15cm": "0.00", "ALIGERADA 17cm": "0.00", ...},
        ...
      },
      ...
    }
    """
    return {}


def process_pdf(file_bytes: bytes) -> dict:
    text, tables = extract_text_and_tables(file_bytes)
    productos = product_extract(text)

    result: dict[str, list[dict]] = {}
    for producto in productos:
        display = DISPLAY_NAMES.get(producto, producto.title())
        divisiones = extract_divisiones(text, tables, producto)
        result[display] = [{"Divisiones": divisiones}]
    return result
