import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Form 

from extractor import process_pdf

app = FastAPI(title="PDF Extractor API", version="1.0.0")


@app.get("/")
def root():
    return {"status": "ok", "message": "PDF Extractor API. POST a PDF to /extract"}


@app.post("/extract")
async def extract(product:  str = Form(...), file: UploadFile = File(...)):
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="The file must be a PDF.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        result = process_pdf(file_bytes, product)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")

    return {
        **result
    }


if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8081,reload=True,reload_includes=["*.py"],reload_excludes=["venv/*", ".venv/*", "**/site-packages/*"],)
