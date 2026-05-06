"""
Extracción de divisiones para el producto PRELOSAS.

Identifica las tablas de metrados (header `NIVEL ... COSTO`) y las clasifica
en SOTANOS / TORRE_A / TORRE_B (RESUMEN se descarta porque es consolidado).
"""

LOSA_COLUMNS = [
    "ALIGERADA 15cm",
    "ALIGERADA 17cm",
    "ALIGERADA 20cm",
    "ALIGERADA 23cm",
    "ALIGERADA 25cm",
    "MACIZA",
    "ALIGERADA 20cm 2 Direcciones",
    "ALIGERADA 25cm 2 Direcciones",
]

SKIP_NIVELES = {"SUBTOTAL", "TOTAL", "NIVEL"}


def _flat(row: list) -> str:
    return " ".join(str(c or "").strip().upper() for c in row)


def _is_metrado_table(table: list[list]) -> bool:
    for row in table:
        flat = _flat(row)
        if flat.strip():
            return "NIVEL" in flat and "COSTO" in flat
    return False


def _get_division_name(table: list[list]) -> str:
    """
    Reglas:
      - CISTERNA o SÓTANO en la primera fila de datos → SOTANOS
      - TORRE A y TORRE B presentes en los datos     → RESUMEN
      - PISO con >15 filas                           → TORRE_A
      - PISO con ≤15 filas                           → TORRE_B
    """
    data_rows = []
    skipped_header = False
    for row in table:
        if not skipped_header:
            if _flat(row).strip():
                skipped_header = True
            continue
        if any(c for c in row if c and str(c).strip()):
            data_rows.append(row)

    if not data_rows:
        return "DESCONOCIDA"

    all_data_text = " ".join(_flat(r) for r in data_rows)
    first_data = _flat(data_rows[0])

    if "TORRE A" in all_data_text and "TORRE B" in all_data_text:
        return "RESUMEN"

    if "CISTERNA" in first_data or "SOTANO" in first_data.replace("Ó", "O"):
        return "SOTANOS"

    if "PISO" in all_data_text:
        piso_count = sum(1 for r in data_rows if "PISO" in _flat(r))
        return "TORRE_A" if piso_count > 15 else "TORRE_B"

    return "DESCONOCIDA"


def _parse_metrado_rows(table: list[list]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    skipped_header = False

    for row in table:
        if not skipped_header:
            if _flat(row).strip():
                skipped_header = True
            continue

        nivel = str(row[0] or "").strip()
        if not nivel or any(kw in nivel.upper() for kw in SKIP_NIVELES):
            continue

        row_data: dict[str, str] = {}
        for col_idx, col_name in enumerate(LOSA_COLUMNS, start=1):
            if col_idx < len(row):
                val = str(row[col_idx] or "0.00").strip()
                val = val.replace(" ", "")
                row_data[col_name] = val

        result[nivel] = row_data

    return result


def extract_divisiones(text: str, tables: list[list[list[str]]]) -> dict:
    divisiones: dict = {}
    for idx, table in enumerate(tables):
        if not _is_metrado_table(table):
            continue
        div_name = _get_division_name(table)
        if div_name in ("DESCONOCIDA", "RESUMEN"):
            continue
        niveles = _parse_metrado_rows(table)
        if niveles:
            divisiones[div_name] = niveles
            print(f"  [{idx}] -> division '{div_name}': {len(niveles)} niveles")
    return divisiones
