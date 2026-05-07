"""
Extracción de divisiones para el producto PRELOSAS.

Identifica las tablas de metrados (header `NIVEL ... COSTO`) y las clasifica
en SOTANOS / TORRE_A / TORRE_B (RESUMEN se descarta porque es consolidado).
"""

def _flat(row: list) -> str:
    return " ".join(str(c or "").strip().upper() for c in row)


def _has_metrado_header(table: list[list]) -> bool:
    """
    Regla estricta: la primera fila NO vacía cumple
      - row[0]  == "NIVEL"
      - row[-2] == "COSTO"
      - row[-1] is None
    """
    for row in table:
        if any(c for c in row if c and str(c).strip()):
            if len(row) < 2:
                return False
            first = str(row[0] or "").strip().upper()
            penultimo = str(row[-2] or "").strip().upper()
            ultimo = row[-1]
            return first == "NIVEL" and penultimo == "COSTO" and ultimo is None
    return False


def filtrar_tablas(tables: list[list[list[str]]]) -> list[list[list[str]]]:
    """
    Devuelve solo las tablas de metrados de PRELOSAS — las que arrancan con
    una fila tipo `['NIVEL', ..., 'COSTO', None]`.

    Descarta:
      - Tablas de metadatos (1 columna, sin NIVEL).
      - Tabla de PRECIO UNITARIO (header con NIVEL pero sin COSTO/None al final).
      - Tablas de acero, ratios, etc.
    """
    return [t for t in tables if _has_metrado_header(t)]


def extraer_niveles(table: list[list]) -> list[str]:
    """
    Devuelve los niveles (primera columna) de una tabla filtrada, en orden.

    - Salta el header (primera fila no vacía, que es `['NIVEL', ...]`).
    - Se detiene al toparse con `SubTotal` (o `Total`) — esas filas ya no son niveles.
    - Salta filas vacías.

    Ejemplo (FOVIPOL): ['CISTERNA', 'SOTANO 3', 'SOTANO 2', ..., 'PISO 23'].
    """
    niveles: list[str] = []
    skipped_header = False

    for row in table:
        if not row:
            continue

        first = str(row[0] or "").strip()

        # Saltar el header (primera fila no vacía)
        if not skipped_header:
            if first:
                skipped_header = True
            continue

        # Detenerse al primer SubTotal / Total — ya no son niveles
        if first.upper().startswith("SUBTOTAL") or first.upper().startswith("TOTAL"):
            break

        if not first:
            continue

        niveles.append(first)

    return niveles


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


def calcular_disgregado_por_nivel(table: list[list]) -> dict[str, str]:
    """
    Para cada nivel de la tabla, suma sus valores disgregados (todas las columnas
    de losa, excluyendo `NIVEL` al inicio y `COSTO`+`None` al final).

    Ej. fila `['SOTANO 3', '1 355.88', '0.00', '95.36', '0.00', '349.74', '0.00', 'S/ ...', None]`
        → suma de `row[1:-2]` = 1800.98
        → `{"SOTANO 3": "1800.98"}`

    Salta el header, ignora filas vacías, y se detiene al toparse con
    `SubTotal` o `Total`.
    """
    result: dict[str, str] = {}
    skipped_header = False

    for row in table:
        if not row:
            continue

        first = str(row[0] or "").strip()

        if not skipped_header:
            if first:
                skipped_header = True
            continue

        if first.upper().startswith("SUBTOTAL") or first.upper().startswith("TOTAL"):
            break

        if not first:
            continue

        total = 0.0
        for cell in row[1:-2]:
            try:
                cleaned = str(cell or "0").strip().replace(" ", "")
                total += float(cleaned)
            except (ValueError, TypeError):
                continue
        result[first] = f"{total:.2f}"

    return result


def extract_divisiones(text: str, tables: list[list[list[str]]]) -> dict:
    """
    Asume `tables` ya viene filtrado por `filtrar_tablas`.

    - 1 tabla : devuelve {"GLOBAL": {nivel: total_disgregado_str}}.
    - 2+ tablas: devuelve {"Divisiones": {division: {nivel: total_disgregado_str}}}.
    - 0 tablas: devuelve {}.

    El caller (process_pdf) hace `entry.update(...)` con el resultado, así
    "GLOBAL" o "Divisiones" se insertan directo en el entry.
    """
    if not tables:
        return {}

    if len(tables) == 1:
        global_data = calcular_disgregado_por_nivel(tables[0])
        if global_data:
            print(f"  [solo 1 tabla] -> GLOBAL: {len(global_data)} niveles")
            return {"GLOBAL": global_data}
        return {}

    divisiones: dict = {}
    for idx, table in enumerate(tables):
        div_name = _get_division_name(table)
        if div_name in ("DESCONOCIDA", "RESUMEN"):
            continue
        data = calcular_disgregado_por_nivel(table)
        if data:
            divisiones[div_name] = data
            print(f"  [{idx}] -> division '{div_name}': {len(data)} niveles")
    return {"Divisiones": divisiones} if divisiones else {}


def _parse_subtotal_row(table: list[list]) -> dict[str, str]:
    """
    Devuelve `{columna: valor_str}` leyendo dinámicamente el header y la fila
    `SubTotal` de la misma tabla.

    - Columnas: header[1:-2] (sin `NIVEL`, sin `COSTO`, sin `None`).
    - Valores : subtotal_row[1:-2] (mismas posiciones).
    - El nombre de columna se normaliza reemplazando `\\n` por un espacio.
    - El valor se limpia de espacios internos (ej. `'3 862.33' → '3862.33'`).
    """
    header = next(
        (row for row in table if any(c for c in row if c and str(c).strip())),
        None,
    )
    if header is None:
        return {}

    subtotal_row = next(
        (row for row in table
         if row and str(row[0] or "").strip().upper().startswith("SUBTOTAL")),
        None,
    )
    if subtotal_row is None:
        return {}

    cols = header[1:-2]
    vals = subtotal_row[1:-2]

    result: dict[str, str] = {}
    for col, val in zip(cols, vals):
        if col is None:
            continue
        col_name = str(col).replace("\n", " ").strip()
        if not col_name:
            continue
        val_str = str(val or "0.00").strip().replace(" ", "")
        result[col_name] = val_str
    return result


def extract_subtotales_disgregados(text: str, tables: list[list[list[str]]]) -> dict[str, str]:
    """
    Asume `tables` ya viene filtrado por `filtrar_tablas`.

    - Si hay 1 sola tabla, su `SubTotal` interno es el subtotal global.
    - Si hay varias, busca la tabla `RESUMEN` y lee su `SubTotal`.
    """
    if len(tables) == 1:
        return _parse_subtotal_row(tables[0])

    for table in tables:
        if _get_division_name(table) == "RESUMEN":
            return _parse_subtotal_row(table)
    return {}


def _total_para_1_tabla(table: list[list]) -> str:
    """
    Caso 1 tabla: localiza la fila cuyo `row[0]` empieza con 'Total' (no 'SubTotal'),
    toma `row[1]` y lo normaliza a string con 2 decimales.

    Ej. fila `['Total', '26 550.82', None, ..., 'I.G.V.']` → `'26550.82'`.
    Devuelve `'0.00'` si no encuentra la fila o el valor no es parseable.
    """
    for row in table:
        if not row:
            continue
        first = str(row[0] or "").strip().upper()
        if first.startswith("TOTAL") and not first.startswith("SUBTOTAL"):
            if len(row) >= 2:
                raw = str(row[1] or "0").strip().replace(" ", "")
                try:
                    return f"{float(raw):.2f}"
                except (ValueError, TypeError):
                    return "0.00"
    return "0.00"


def _sumar_subtotales(subtotales: dict[str, str]) -> str:
    """Suma los valores numéricos de un dict de subtotales y formatea con 2 decimales."""
    total = 0.0
    for val in subtotales.values():
        try:
            total += float(val)
        except (ValueError, TypeError):
            continue
    return f"{total:.2f}"


def calcular_total(text: str, tables: list[list[list[str]]]) -> str:
    """
    Asume `tables` ya viene filtrado por `filtrar_tablas`.

    - 1 tabla : lee el `total` directamente de la fila 'Total' de la tabla
                (`_total_para_1_tabla`).
    - 2+ tablas: por ahora suma los valores de `extract_subtotales_disgregados`
                (`_sumar_subtotales`). TODO — refinar cuando el usuario lo guíe.
    """
    if not tables:
        return "0.00"
    if len(tables) == 1:
        return _total_para_1_tabla(tables[0])
    return _sumar_subtotales(extract_subtotales_disgregados(text, tables))
