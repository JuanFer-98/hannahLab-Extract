# PDF Extractor API — Notas para Claude

Este archivo es contexto para Claude Code. **Se auto-alimenta**: cada vez que el usuario pida una mejora o cambio, Claude debe agregar una entrada en la sección "Historial de mejoras" al final.

---

## Resumen del proyecto

API en FastAPI que recibe un PDF + `product` (string que indica el tipo de producto) y devuelve un JSON estructurado con `Divisiones` (división → nivel → nomenclatura → valor string).

El endpoint recibe **dos campos** en multipart/form-data: `file` (PDF) y `product` (uno de los keys de `DISPLAY_NAMES`). El `product` viene del cliente, **no se detecta del texto**.

Las reglas de extracción de divisiones **se construyen incrementalmente**: el usuario las irá especificando una a una.

## Estructura de archivos

- [main.py](main.py) — App FastAPI. Endpoint `POST /extract` (multipart, campos `file` + `product`). Arranca uvicorn en `127.0.0.1:8080`.
- [extractor.py](extractor.py) — Lectura de PDF con **pdfplumber** (texto + tablas), catálogo `DISPLAY_NAMES` (producto → lista de nomenclaturas), construcción de divisiones, orquestación.
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
- **Reglas incrementales**: `extract_divisiones` arranca como stub (`return {}`). Cada regla nueva del usuario se va agregando a esa función. El código que no aporta al objetivo actual se elimina (no se acumula código muerto).
- **Valores como string, no float**: el ejemplo del usuario muestra `"ALIGERADA 15cm": "0.00"` (entrecomillado). Los metrados se conservan como string para preservar el formato original del PDF.

## Cómo correr

```powershell
$env:PYTHONHOME=$null; $env:PYTHONPATH=$null
.\venv\Scripts\Activate.ps1
python main.py
```

Swagger UI: http://127.0.0.1:8080/docs

## Forma del JSON de respuesta (objetivo)

Input: `product=PRELOSAS` y un PDF con varias tablas.

```jsonc
{
  "PRELOSAS": [
    {
      "Divisiones": {
        "TORRE1": {
          "CISTERNA": {
            "Aligerada 1D 25cm (A=15) (T) (C=38)": "0.00",
            "Aligerada 2D 25cm": "0.00"
            // … resto de subproductos de DISPLAY_NAMES["PRELOSAS"]
          }
          // … más niveles
        }
        // … más divisiones (TORRE2, SOTANOS, …)
      }
    }
  ]
}
```

Si `len(tables) <= 1`, el `entry` es `{}` y queda `{"PRELOSAS": [{}]}`.

Hoy `Divisiones` viene `{}` aunque haya tablas (porque la lógica de detección de divisiones/niveles aún no está implementada). Se irá llenando conforme el usuario aporte reglas.

## Funciones públicas de `extractor.py`

- `extract_text_and_tables(file_bytes) -> (str, list[list[list[str]]])` — texto concatenado de todas las páginas + lista plana de tablas (cada tabla = lista de filas, cada fila = lista de celdas).
- `debug_print_tables(tables_by_page)` — helper de debug para imprimir las tablas en consola. (Nota: asume estructura por página; si se llama con la lista plana de `extract_text_and_tables`, la salida puede no agruparse bien.)
- `extract_divisiones(text, tables, producto) -> dict` — **stub**. Construye `{"TORRE1": {"CISTERNA": {"Aligerada 1D 25cm (A=15) (T) (C=38)": "0.00", …}, …}, …}` usando las nomenclaturas de `DISPLAY_NAMES[producto]`. Pendiente de reglas del usuario.
- `process_pdf(file_bytes, product) -> dict` — orquesta todo. Lee el PDF, y si hay >1 tabla incluye `Divisiones`. Devuelve `{product: [entry]}`.

## TODOs / pendientes

- [ ] Implementar `extract_divisiones` conforme el usuario aporte reglas para cada división (TORRE1, TORRE2, SOTANOS…) y nivel (CISTERNA, SOTANO 6, PISO 1…). El stub ya recibe `producto`, así que puede consultar `DISPLAY_NAMES[producto]` para saber qué columnas extraer de las tablas.
- [ ] Definir si la lista al lado del producto (`"PRELOSAS": [...]`) puede tener más de un elemento (ej. múltiples instancias/cotizaciones del mismo producto en un solo PDF) o siempre será de longitud 1.
- [ ] Validar el `product` recibido contra los keys de `DISPLAY_NAMES` y devolver 400 si no es válido (hoy se acepta cualquier string).
- [ ] Decidir si `debug_print_tables` debe ajustar su firma a la lista plana actual o si `extract_text_and_tables` debe pasar a devolver tablas agrupadas por página.

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
