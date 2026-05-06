import requests

def download_pdf_from_url(url: str) -> bytes:
    if "dropbox.com" in url and "dl=0" in url:
        url = url.replace("dl=0", "dl=1")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error descargando PDF: {str(e)}")

    return response.content