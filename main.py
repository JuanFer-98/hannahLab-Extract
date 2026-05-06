import uvicorn
from fastapi import FastAPI, Form, HTTPException

from extractor import process_pdf
from dropbox.converDropbox import convertdrop


app = FastAPI(title="PDF Extractor API", version="1.0.0")


@app.get("/")
def root():
    return {"status": "ok", "message": "PDF Extractor API. POST a PDF to /extract"}


# Endpoint multipart deshabilitado: el flujo oficial entra por /extract-from-url.
# @app.post("/extract")
# async def extract(product:  str = Form(...), file: UploadFile = File(...),linkdrop:  str = Form(...)):
#     if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
#         raise HTTPException(status_code=400, detail="The file must be a PDF.")
#
#     file_bytes = await file.read()
#     if not file_bytes:
#         raise HTTPException(status_code=400, detail="Empty file.")
#
#     try:
#         result = process_pdf(file_bytes, product)
#         descargapdf = convertdrop(linkdrop)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")
#
#     return {
#         **result
#     }


@app.post("/extract-from-url")
def extract_from_url(
    url: str = Form(..., description="URL temporal del PDF (Dropbox)"),
    product: str = Form(..., description="Producto a extraer (ej. PRELOSAS)"),
):
    if not url:
        raise HTTPException(status_code=400, detail="url requerida")
    if not product:
        raise HTTPException(status_code=400, detail="product requerido")

    file_path = None
    try:
        # 1. Descargar el PDF desde la URL temporal de Dropbox a docs/
        file_path = convertdrop(url)

        # 2. Leer bytes y procesar con el handler del producto
        file_bytes = file_path.read_bytes()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file.")

        result = process_pdf(file_bytes, product)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")
    # finally:
    #     # 3. Borrar el archivo descargado (deshabilitado: el usuario los limpia a mano)
    #     if file_path is not None and file_path.exists():
    #         try:
    #             file_path.unlink()
    #         except Exception:
    #             pass


if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8081,reload=True,reload_includes=["*.py"],reload_excludes=["venv/*", ".venv/*", "**/site-packages/*"],)
