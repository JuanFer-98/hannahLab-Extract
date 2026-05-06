
Listo. Para verificar la conexión end-to-end:

Levantá el FastAPI: python main.py (debe quedar en 127.0.0.1:8080).
Levantá el gateway.
Probá desde Swagger del gateway (<http://localhost>:<PORT>/api/v2/docs) → endpoint POST /document-parser/extract/metrados/file → subí un PDF.
