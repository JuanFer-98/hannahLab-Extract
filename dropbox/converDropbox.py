import re
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# Caracteres invisibles que se cuelan al copiar/pegar URLs (ZWSP, WORD JOINER, BOM, etc.)
_INVISIBLE_CHARS = re.compile(r"[​-\u200F⁠-⁯﻿]")


def _sanitize_url(url: str) -> str:
    """Quita caracteres invisibles y re-codifica path/query para evitar errores ASCII."""
    cleaned = _INVISIBLE_CHARS.sub("", url).strip()
    parts = urlsplit(cleaned)
    return urlunsplit(
        parts._replace(
            path=quote(parts.path, safe="/%"),
            query=quote(parts.query, safe="&=?%"),
        )
    )


def convertdrop(url: str) -> Path:
    """Descarga un PDF desde una URL temporal de Dropbox a la carpeta docs/.
    Devuelve el path absoluto al archivo descargado."""
    if not url:
        raise ValueError("url requerida")

    # Dropbox shared links a veces vienen con dl=0 (preview); forzamos descarga directa
    if "dropbox.com" in url and "dl=0" in url:
        url = url.replace("dl=0", "dl=1")

    safe = _sanitize_url(url)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DOCS_DIR / f"{uuid.uuid4().hex}.pdf"

    with urllib.request.urlopen(safe) as resp:
        file_path.write_bytes(resp.read())

    return file_path
