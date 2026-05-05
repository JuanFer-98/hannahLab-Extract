# PDF Extractor API — Notas para Claude

Este archivo es contexto para Claude Code. **Se auto-alimenta**: cada vez que el usuario pida una mejora o cambio, Claude debe agregar una entrada en la sección "Historial de mejoras" al final.

---

## Resumen del proyecto

API en FastAPI que recibe un PDF (cotizaciones de prefabricados de concreto — Beton Decken / propuestas tipo Pacific Soul) y devuelve un JSON estructurado con:
- El **producto** principal detectado.
- Los **bloques** del documento (secciones tipo SÓTANOS, TORRE A, TORRE B…), con sus niveles (SÓTANO 6, PISO 1…) y los metrados por nomenclatura/columna (ALIGERADA 15cm, MACIZA…), más subtotal por bloque.

Las reglas de extracción de bloques **se construyen incrementalmente**: el usuario las irá especificando una a una.

## Estructura de archivos

- [main.py](main.py) — App FastAPI. Endpoint `POST /extract` (multipart, campo `file`). Arranca uvicorn en `127.0.0.1:8080`.
- [extractor.py](extractor.py) — Lectura de PDF con **pdfplumber** (texto + tablas), detección de producto, construcción de bloques, orquestación.
- [requirements.txt](requirements.txt) — fastapi, uvicorn[standard], python-multipart, pdfplumber.
- `venv/` — Entorno virtual Python 3.14.

## Decisiones / convenciones (no obvias)

- **Puerto 8080** (no 8000): el 8000 cae en el rango excluido de Hyper-V/WSL en Windows 11 → `WinError 10013`.
- **`reload_excludes`**: el watcher de uvicorn ignora `venv/` y `**/site-packages/*`. OneDrive toca timestamps al sincronizar y si no se excluye, dispara recargas en bucle infinito.
- **Antes de correr Python**: `$env:PYTHONHOME=$null; $env:PYTHONPATH=$null`. La instalación de `C:\GitStack\python` está rota (`SyntaxError` en `encodings/__init__.py`) y las variables de entorno globales del usuario apuntan ahí. Hay que neutralizarlas en cada sesión hasta que se limpien del sistema.
- **pdfplumber, no pypdf**: los PDFs de cotización contienen tablas estructuradas. `pdfplumber` expone `page.extract_tables()` con celdas separadas, lo que permite leer metrados por nivel/columna sin parsear texto plano. `pypdf` solo daba texto continuo y se perdía la geometría de la tabla.
- **`product_extract` con orden por longitud descendente**: necesario para que `ESPECIALES (PRELOSAS)` no produzca un falso positivo de `PRELOSAS`. Las apariciones más largas se "tachan" antes de buscar las cortas.
- **Reglas incrementales**: `extract_bloques` arranca como stub (`return {}`). Cada regla nueva del usuario se va agregando a esa función. El código que no aporta al objetivo actual se elimina (no se acumula código muerto).
- **Multi-producto en la salida**: el JSON destino tiene un key por cada producto detectado, en su forma display (`PRELOSAS` → `Prelosa`). Cada producto va a una lista de objetos, cada objeto con un `Divisiones` (división → nivel → nomenclatura → valor string). Si `product_extract` no detecta nada, se devuelve `{}`.
- **`DISPLAY_NAMES` mapping**: traducción `PRELOSAS → Prelosa`, `PREVIGAS → Previga`, etc. Es el formato que el usuario quiere ver en el JSON. Vive en `extractor.py`.
- **Valores como string, no float**: el ejemplo del usuario muestra `"ALIGERADA 15cm": "0.00"` (entrecomillado). Los metrados se conservan como string para preservar el formato original del PDF.

## Cómo correr

```powershell
$env:PYTHONHOME=$null; $env:PYTHONPATH=$null
.\venv\Scripts\Activate.ps1
python main.py
```

Swagger UI: http://127.0.0.1:8080/docs

## Forma del JSON de respuesta (objetivo)

```jsonc
{
  "Prelosa": [
    {
      "Divisiones": {
        "TORRE1": {
          "CISTERNA": {
            "ALIGERADA 15cm": "0.00",
            "ALIGERADA 17cm": "0.00"
            // … resto de columnas como strings
          }
          // … más niveles
        }
        // … más divisiones (TORRE2, SOTANOS, …)
      }
    }
  ]
  // … más productos (Previga, Friso, …) si se detectan
}
```

Hoy `Divisiones` viene `{}`. Se irá llenando conforme el usuario aporte reglas.

## Funciones públicas de `extractor.py`

- `extract_text_and_tables(file_bytes) -> (str, list[list[list[str]]])` — texto concatenado de todas las páginas + lista de tablas (cada tabla = lista de filas, cada fila = lista de celdas).
- `product_extract(text) -> list[str]` — devuelve los nombres de `PRODUCT_NAMES` que aparecen en el texto. Case-insensitive, evita falsos positivos por substring.
- `extract_divisiones(text, tables, producto) -> dict` — **stub**. Construye el dict `{"TORRE1": {"CISTERNA": {"ALIGERADA 15cm": "0.00", …}, …}, …}` para un producto. Pendiente de reglas del usuario.
- `process_pdf(file_bytes) -> dict` — orquesta todo. Para cada producto detectado por `product_extract`, traduce con `DISPLAY_NAMES` y construye `{display: [{"Divisiones": {…}}]}`. Soporta multi-producto.

## TODOs / pendientes

- [ ] Implementar `extract_divisiones` conforme el usuario aporte reglas para cada división (TORRE1, TORRE2, SOTANOS…) y nivel (CISTERNA, SOTANO 6, PISO 1…).
- [ ] Confirmar si los keys `DISPLAY_NAMES` deben mantenerse en singular tipo `Prelosa`/`Previga`/etc. o si el usuario quiere otro mapping.
- [ ] Definir si la lista al lado del producto (`"Prelosa": [...]`) puede tener más de un elemento (ej. múltiples instancias/cotizaciones del mismo producto en un solo PDF) o siempre será de longitud 1.

## Historial de mejoras

> Cada entrada: fecha (ISO), descripción breve, archivos tocados.

- **2026-05-04** — Estructura inicial del proyecto: venv, FastAPI app con endpoint `/extract`, extractor con pypdf, reglas genéricas (emails/teléfonos/URLs/conteos). Archivos: `main.py`, `extractor.py`, `requirements.txt`.
- **2026-05-04** — Fix de puerto (8000 → 8080) y `reload_excludes` para evitar bucle de recargas con OneDrive sincronizando `venv/`. Archivo: `main.py`.
- **2026-05-04** — Clasificador multi-producto + catálogo inicial de 13 familias con alias y matching tolerante. Extracción de metadatos del cliente y resumen financiero global (SUBTOTAL/IGV/TOTAL). Archivos nuevos: `classifier.py`, `nomenclaturas.json`. Modificado: `extractor.py`.
- **2026-05-04** — Refactor del clasificador: las nomenclaturas pasan a ser **reglas hardcodeadas** en `classifier.py` (no JSON externo). Cada regla tiene `identificador`, `producto`, `unidad_medida`, `descripcion` y un `re.Pattern` doble (código literal `[MZ]` o texto descriptivo). Eliminado `nomenclaturas.json`. Archivo: `classifier.py`.
- **2026-05-05** — Añadida `product_extract(text) -> list[str]` en `extractor.py` con `PRODUCT_NAMES` (las 13 familias). Búsqueda case-insensitive con orden por longitud descendente para evitar falsos positivos (`ESPECIALES (PRELOSAS)` no dispara `PRELOSAS`). Archivo: `extractor.py`.
- **2026-05-05** — **Cambio de motor de extracción**: `pypdf` → `pdfplumber` (para leer tablas estructuradas, no solo texto plano). Reescrita `extractor.py` enfocada al nuevo objetivo: `process_pdf` ahora devuelve `{"producto": str|None, "bloques": {}}`. **Eliminados** por ya no aportar: `classifier.py` (clasificador con identificadores `[MZ]/[PV70C35]/...`), funciones `apply_rules`/`extract_metadata`/`extract_financial_summary` y sus regex (emails, teléfonos, dinero, metadata del cliente). `extract_bloques` queda como stub a la espera de reglas. Archivos modificados: `extractor.py`, `requirements.txt`. Eliminados: `classifier.py`.
- **2026-05-05** — Cambio de forma del JSON de salida a `{<DisplayProducto>: [{"Divisiones": {<DIV>: {<NIVEL>: {<NOMENC>: "<valor_str>"}}}}]}`. Renombrada `extract_bloques` → `extract_divisiones(text, tables, producto)` (sigue como stub). Añadido `DISPLAY_NAMES` con la traducción por producto (`PRELOSAS → Prelosa`, etc., 13 entradas). `process_pdf` itera todos los productos detectados y arma el dict resultado (multi-producto soportado nativamente). Archivo: `extractor.py`.
