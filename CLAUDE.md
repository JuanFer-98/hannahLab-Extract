# PDF Extractor API — Notas para Claude

Este archivo es contexto para Claude Code. **Se auto-alimenta**: cada vez que el usuario pida una mejora o cambio, Claude debe agregar una entrada en la sección "Historial de mejoras" al final.

---

## Resumen del proyecto

API en FastAPI que recibe un PDF + `product` (string que indica el tipo de producto) y devuelve un JSON estructurado con `Divisiones` (división → nivel → nomenclatura → valor string).

El endpoint recibe **dos campos** en multipart/form-data: `file` (PDF) y `product` (uno de los keys de `DISPLAY_NAMES`). El `product` viene del cliente, **no se detecta del texto**.

Las reglas de extracción de divisiones **se construyen incrementalmente**: el usuario las irá especificando una a una.

## Estructura de archivos

- [main.py](main.py) — App FastAPI. Endpoint `POST /extract` (multipart, campos `file` + `product`). Arranca uvicorn en `127.0.0.1:8080`. Devuelve 400 si `product` no está en `DISPLAY_NAMES`.
- [extractor.py](extractor.py) — Solo código **genérico**: `pdfplumber` para texto+tablas, `DISPLAY_NAMES` (catálogo), `PRODUCT_HANDLERS` (dispatcher), `process_pdf`. **No tiene lógica específica de ningún producto.**
- [PRODUCTOS/](PRODUCTOS/) — Paquete con un módulo por producto. Import: `import PRODUCTOS.prelosas as prelosas`.
  - [PRODUCTOS/__init__.py](PRODUCTOS/__init__.py) — Marker del paquete (vacío).
  - [PRODUCTOS/prelosas.py](PRODUCTOS/prelosas.py) — Lógica específica de **PRELOSAS**: detecta tablas de metrados (header `NIVEL ... COSTO`), las clasifica en `SOTANOS`/`TORRE_A`/`TORRE_B`/`RESUMEN`, parsea filas y devuelve `{division: {nivel: {nomenclatura: valor_str}}}`.
  - (Futuro) `PRODUCTOS/previgas.py`, `PRODUCTOS/frisos.py`, etc.
- [requirements.txt](requirements.txt) — fastapi, uvicorn[standard], python-multipart, pdfplumber.
- `venv/` — Entorno virtual Python 3.14.

## Decisiones / convenciones (no obvias)

- **Puerto 8080** (no 8000): el 8000 cae en el rango excluido de Hyper-V/WSL en Windows 11 → `WinError 10013`.
- **`reload_excludes`**: el watcher de uvicorn ignora `venv/` y `**/site-packages/*`. OneDrive toca timestamps al sincronizar y si no se excluye, dispara recargas en bucle infinito.
- **Antes de correr Python**: `$env:PYTHONHOME=$null; $env:PYTHONPATH=$null`. La instalación de `C:\GitStack\python` está rota (`SyntaxError` en `encodings/__init__.py`) y las variables de entorno globales del usuario apuntan ahí. Hay que neutralizarlas en cada sesión hasta que se limpien del sistema.
- **pdfplumber, no pypdf**: los PDFs de cotización contienen tablas estructuradas. `pdfplumber` expone `page.extract_tables()` con celdas separadas, lo que permite leer metrados por nivel/columna sin parsear texto plano. `pypdf` solo daba texto continuo y se perdía la geometría de la tabla.
- **`product` viene como input**: el usuario decidió que el cliente envía el tipo de producto (`PRELOSAS`, `PREVIGAS`, etc.) como form field, en vez de detectarlo del texto. Esto eliminó la necesidad de `product_extract` y `PRODUCT_NAMES` (borrados).
- **`DISPLAY_NAMES = dict[str, list[str]]`**: el catálogo. Cada key es uno de los 13 productos válidos; el value es la lista de nomenclaturas/subproductos esperados en el PDF de ese producto (sacadas de la tabla original con columna NOMENCLATURA GENERAL). Lo usa `extract_divisiones` para saber qué columnas buscar en las tablas. **No es un display name al estilo "Prelosa singular"** — el nombre se mantiene por compatibilidad, pero la semántica es "subproductos del producto".
- **Top-level key del JSON = `product` literal**: el dict resultado se construye `{product: [...]}` con el string que llega del input, sin transformación. No hay traducción a singular.
- **Conditional `Divisiones`**: se inserta solo si `len(tables) > 1`. Si el PDF tiene 0 o 1 tablas, el resultado es `{product: [{}]}` (lista con objeto vacío). Si tiene >1, es `{product: [{"Divisiones": {...}}]}`.
- **Un archivo por producto en `PRODUCTOS/` + dispatcher**: `extractor.py` es genérico (lectura de PDF + dispatch). Cada producto vive en `PRODUCTOS/<nombre>.py` y expone **3 funciones**: `extract_divisiones(text, tables)`, `extract_subtotales_disgregados(text, tables)`, `calcular_total(subtotales)`. `extractor.PRODUCT_HANDLERS` mapea `"PRELOSAS"` → **el módulo entero** (no a una función), así `process_pdf` invoca las 3 con `handler.<nombre>`. Para añadir un producto: (1) crear `PRODUCTOS/<nuevo>.py` con las 3 funciones, (2) importarlo en `extractor.py`, (3) agregar una línea al dict.
- **Detección de tablas — NO es por nombre**: `pdfplumber` no expone "nombres de tabla". La clasificación es por contenido en 2 niveles (en `PRODUCTOS/prelosas.py`): nivel 1 `_is_metrado_table` (header tiene `NIVEL` + `COSTO`), nivel 2 `_get_division_name` (filas de datos contienen `CISTERNA`/`SÓTANO` → SOTANOS, `TORRE A` + `TORRE B` → RESUMEN, `PISO` con conteo >15 → TORRE_A, ≤15 → TORRE_B).
- **Carpeta `PRODUCTOS` en MAYÚSCULAS**: el usuario lo eligió así. Python conserva la diferencia mayúscula/minúscula en imports aunque Windows tenga FS case-insensitive — el import literal es `import PRODUCTOS.prelosas as prelosas`.
- **Validación temprana de `product`**: `process_pdf` lanza `ValueError` si `product` no es key de `DISPLAY_NAMES`. `main.py` lo traduce a 400. Así se rechaza antes de leer el PDF.
- **Reglas incrementales**: cuando un producto aún no tenga handler en `PRODUCT_HANDLERS`, el `Divisiones` queda `{}` aunque haya tablas. Se va llenando producto por producto.
- **Valores como string, no float**: el ejemplo del usuario muestra `"ALIGERADA 15cm": "0.00"` (entrecomillado). Los metrados se conservan como string para preservar el formato original del PDF.

## Cómo correr

```powershell
$env:PYTHONHOME=$null; $env:PYTHONPATH=$null
.\venv\Scripts\Activate.ps1
python main.py
```

Swagger UI: http://127.0.0.1:8080/docs

## Forma del JSON de respuesta

Input: `product=PRELOSAS` y un PDF con varias tablas.

```jsonc
{
  "PRELOSAS": [
    {
      "Divisiones": {
        "SOTANOS": {
          "CISTERNA": {"ALIGERADA 15cm": "0.00", ..., "MACIZA": "247.49", ...},
          "SÓTANO 6": {...}
          // ...
        },
        "TORRE_A": { "PISO 1": {...}, ..., "AZOTEA": {...} },
        "TORRE_B": { "PISO 1": {...}, ..., "AZOTEA": {...} }
      },
      "subtotales_disgregados": {
        "ALIGERADA 15cm": "258.86",
        "ALIGERADA 17cm": "1003.37",
        "ALIGERADA 20cm": "8532.12",
        "ALIGERADA 23cm": "1273.02",
        "ALIGERADA 25cm": "596.27",
        "MACIZA": "3913.86",
        "ALIGERADA 20cm 2 Direcciones": "3031.24",
        "ALIGERADA 25cm 2 Direcciones": "563.45"
      },
      "total": "19172.19"
    }
  ]
}
```

- `Divisiones` solo aparece cuando `len(tables) > 1`.
- `subtotales_disgregados` y `total` siempre aparecen si el `product` tiene handler (vienen vacíos/`"0.00"` si no se encontró tabla `RESUMEN`).

## API pública

### `extractor.py` (genérico)
- `DISPLAY_NAMES: dict[str, list[str]]` — catálogo de productos válidos y sus nomenclaturas.
- `PRODUCT_HANDLERS: dict[str, ModuleType]` — dispatcher producto → módulo handler.
- `extract_text_and_tables(file_bytes) -> (str, list[list[list[str]]])` — texto concatenado + lista plana de tablas.
- `process_pdf(file_bytes, product) -> dict` — valida `product`, lee el PDF, invoca el handler del producto. Llama `handler.extract_divisiones` (solo si `len(tables) > 1`), `handler.extract_subtotales_disgregados` y `handler.calcular_total`. Devuelve `{product: [entry]}`. Lanza `ValueError` si `product` no es válido.

### Contrato de cada handler en `PRODUCTOS/`
Cada módulo expone:
- `extract_divisiones(text, tables) -> dict` — `{division: {nivel: {nomenclatura: valor_str}}}`.
- `extract_subtotales_disgregados(text, tables) -> dict[str, str]` — `{nomenclatura: valor_str}` desde la tabla RESUMEN.
- `calcular_total(subtotales: dict[str, str]) -> str` — suma los valores y devuelve string con 2 decimales.

### `PRODUCTOS/prelosas.py` (PRELOSAS)
- Detecta tablas con header `NIVEL...COSTO` y las clasifica con `_get_division_name` (SOTANOS / TORRE_A / TORRE_B / RESUMEN) usando heurísticas sobre las filas de datos.
- `extract_divisiones` parsea filas con `_parse_metrado_rows` usando `LOSA_COLUMNS`.
- `extract_subtotales_disgregados` busca la tabla RESUMEN y lee su fila `SubTotal`.
- `calcular_total` suma los valores. **Validado** contra Pacific Soul: 7 niveles SOTANOS, 23 niveles TORRE_A, 10 niveles TORRE_B; subtotales correctos por columna; total = `19172.19` (suma de los 8 subtotales) coincide con el PDF.

### Cómo agregar un producto nuevo (ej. PREVIGAS)
1. Crear `PRODUCTOS/previgas.py` con las 3 funciones del contrato (firma idéntica a las de `prelosas.py`).
2. En `extractor.py`, agregar `import PRODUCTOS.previgas as previgas` y la línea `"PREVIGAS": previgas` a `PRODUCT_HANDLERS`.
3. Listo — `process_pdf` ya rutea automáticamente.

## TODOs / pendientes

- [ ] Implementar handlers para los productos restantes (`previgas.py`, `frisos.py`, etc.) conforme el usuario aporte sus reglas.
- [ ] Mejorar la heurística `TORRE_A` vs `TORRE_B` en `prelosas._get_division_name`: hoy distingue por número de pisos (>15 vs ≤15), lo que falla en proyectos con torres balanceadas. Idealmente identificar por encabezado/título de la tabla.
- [ ] Mapear las columnas detectadas en el PDF (`ALIGERADA 15cm`, `MACIZA`, …) a las nomenclaturas oficiales del catálogo `DISPLAY_NAMES["PRELOSAS"]` (`Aligerada 1D 25cm (A=15) (T) (C=38)`, …) — hoy son strings distintos y no se cruzan.
- [ ] Definir si la lista al lado del producto (`"PRELOSAS": [...]`) puede tener más de un elemento (múltiples instancias del mismo producto en un solo PDF) o siempre será de longitud 1.

## Historial de mejoras

> Cada entrada: fecha (ISO), descripción breve, archivos tocados.

- **2026-05-04** — Estructura inicial del proyecto: venv, FastAPI app con endpoint `/extract`, extractor con pypdf, reglas genéricas (emails/teléfonos/URLs/conteos). Archivos: `main.py`, `extractor.py`, `requirements.txt`.
- **2026-05-04** — Fix de puerto (8000 → 8080) y `reload_excludes` para evitar bucle de recargas con OneDrive sincronizando `venv/`. Archivo: `main.py`.
- **2026-05-04** — Clasificador multi-producto + catálogo inicial de 13 familias con alias y matching tolerante. Extracción de metadatos del cliente y resumen financiero global (SUBTOTAL/IGV/TOTAL). Archivos nuevos: `classifier.py`, `nomenclaturas.json`. Modificado: `extractor.py`.
- **2026-05-04** — Refactor del clasificador: las nomenclaturas pasan a ser **reglas hardcodeadas** en `classifier.py` (no JSON externo). Cada regla tiene `identificador`, `producto`, `unidad_medida`, `descripcion` y un `re.Pattern` doble (código literal `[MZ]` o texto descriptivo). Eliminado `nomenclaturas.json`. Archivo: `classifier.py`.
- **2026-05-05** — Añadida `product_extract(text) -> list[str]` en `extractor.py` con `PRODUCT_NAMES` (las 13 familias). Búsqueda case-insensitive con orden por longitud descendente para evitar falsos positivos (`ESPECIALES (PRELOSAS)` no dispara `PRELOSAS`). Archivo: `extractor.py`.
- **2026-05-05** — **Cambio de motor de extracción**: `pypdf` → `pdfplumber` (para leer tablas estructuradas, no solo texto plano). Reescrita `extractor.py` enfocada al nuevo objetivo: `process_pdf` ahora devuelve `{"producto": str|None, "bloques": {}}`. **Eliminados** por ya no aportar: `classifier.py` (clasificador con identificadores `[MZ]/[PV70C35]/...`), funciones `apply_rules`/`extract_metadata`/`extract_financial_summary` y sus regex (emails, teléfonos, dinero, metadata del cliente). `extract_bloques` queda como stub a la espera de reglas. Archivos modificados: `extractor.py`, `requirements.txt`. Eliminados: `classifier.py`.
- **2026-05-05** — Cambio de forma del JSON de salida a `{<DisplayProducto>: [{"Divisiones": {<DIV>: {<NIVEL>: {<NOMENC>: "<valor_str>"}}}}]}`. Renombrada `extract_bloques` → `extract_divisiones(text, tables, producto)` (sigue como stub). Añadido `DISPLAY_NAMES` con la traducción por producto (`PRELOSAS → Prelosa`, etc., 13 entradas). `process_pdf` itera todos los productos detectados y arma el dict resultado (multi-producto soportado nativamente). Archivo: `extractor.py`.
- **2026-05-05** — `product` pasa a ser **input del endpoint** (form field `product` en `/extract`, junto al `file`). `process_pdf(file_bytes, product)` toma el producto literalmente, sin detectarlo del texto. **`DISPLAY_NAMES` reestructurado** de `dict[str, str]` (display singular) a `dict[str, list[str]]` (lista de subproductos/nomenclaturas por producto, con las 13 familias y sus nomenclaturas tomadas del catálogo original). **`Divisiones` condicional**: solo se inserta cuando `len(tables) > 1`. Top-level key del JSON pasa a ser el `product` recibido literalmente. **Eliminados** por código no usado: `PRODUCT_NAMES`, `product_extract`. Archivos: `extractor.py`, `main.py`.
- **2026-05-05** — Implementación inicial de PRELOSAS dentro de `extractor.py` (helpers `_flat`/`_is_metrado_table`/`_get_division_name`/`_parse_metrado_rows`, constantes `LOSA_COLUMNS`/`SKIP_NIVELES`, función `extract_divisiones`). Detección dinámica de tablas de metrados y clasificación en `SOTANOS`/`TORRE_A`/`TORRE_B`/`RESUMEN`. Archivo: `extractor.py`.
- **2026-05-05** — **Refactor a un archivo por producto + dispatcher**. Movida toda la lógica de PRELOSAS a `prelosas.py` (helpers + `extract_divisiones(text, tables)`). `extractor.py` queda solo con código genérico: `pdfplumber`, `DISPLAY_NAMES`, `PRODUCT_HANDLERS` (dict producto → handler), `process_pdf` (valida `product`, lee PDF, delega al handler). Eliminado el duplicado de `extract_text_and_tables`. Validación de `product` desconocido lanza `ValueError` → `main.py` la traduce a HTTP 400. Para añadir producto nuevo basta crear el archivo y agregar 1 línea al `PRODUCT_HANDLERS`. Archivos: `extractor.py` (reescrito), `prelosas.py` (nuevo), `main.py` (catch `ValueError`).
- **2026-05-05** — **Paquete `PRODUCTOS/`** (mayúsculas, según preferencia del usuario): movido `prelosas.py` a `PRODUCTOS/prelosas.py` con `__init__.py` vacío. Import en `extractor.py`: `import PRODUCTOS.prelosas as prelosas`. **Bug fix** en `prelosas._parse_metrado_rows`: `SKIP_NIVELES` contenía `""` y la condición `any(kw in nivel.upper() for kw in SKIP_NIVELES)` siempre era `True` (porque `"" in cualquier_string` es `True`), lo que hacía que se saltaran todas las filas y la función devolviera `{}`. Removido `""` del set; el chequeo `not nivel` ya cubre filas vacías. Validado con datos reales del PDF Pacific Soul: detecta correctamente SOTANOS (7), TORRE_A (23), TORRE_B (10). Archivos: `PRODUCTOS/__init__.py` (nuevo), `PRODUCTOS/prelosas.py` (movido + fix), `extractor.py` (import actualizado).
- **2026-05-06** — **Subtotales disgregados + total**. Añadidas dos funciones a `PRODUCTOS/prelosas.py`: `extract_subtotales_disgregados(text, tables)` (busca la tabla `RESUMEN` con `_get_division_name`, lee su fila `SubTotal` y devuelve `{columna: valor_str}`) y `calcular_total(subtotales)` (suma los valores y formatea con 2 decimales). Helper privado `_parse_subtotal_row`. **`PRODUCT_HANDLERS` cambia su tipo** de `dict[str, Callable]` a `dict[str, ModuleType]` — ahora mapea producto → módulo entero, así `process_pdf` invoca `handler.extract_divisiones`, `handler.extract_subtotales_disgregados`, `handler.calcular_total` con la misma referencia. Reemplazados los placeholders `entry["subtotales_disgregados"]="tables"`/`entry["total"]="hola mundo"` por las llamadas reales. Validado contra Pacific Soul: total = `19172.19` (= 258.86 + 1003.37 + 8532.12 + 1273.02 + 596.27 + 3913.86 + 3031.24 + 563.45) coincide con el PDF. Archivos: `PRODUCTOS/prelosas.py`, `extractor.py`.
