# download_utils: fetch_alto, fetch_full_document_text
from functools import lru_cache

import requests

from alto_utils import parse_alto


@lru_cache(maxsize=256)
def fetch_alto(urn, page_id):
    url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{page_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
    except requests.RequestException:
        pass
    return None


@lru_cache(maxsize=32)
def fetch_full_document_text(urn, page_ids):
    full_doc_text = ""
    for page_number, page_id in enumerate(page_ids, 1):
        url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{page_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                _, _, _, _, _, page_text = parse_alto(response.text)
                if page_text:
                    full_doc_text += f"=== Side {page_number} ===\n{page_text}\n\n"
            elif response.status_code not in (404, 500):
                full_doc_text += f"=== Side {page_number} ===\n[FEIL: Status {response.status_code}]\n\n"
        except requests.RequestException:
            full_doc_text += f"=== Side {page_number} ===\n[FEIL: Nettverksfeil]\n\n"
    return full_doc_text.strip()
