# download_utils: fetch_alto, fetch_full_document_text
import requests
import streamlit as st
from alto_utils import parse_alto


def fetch_alto(urn, page):
    url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{urn}_{page:04d}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Kunne ikke hente ALTO XML for side {page}. Status: {response.status_code}")
        return None
    
@st.cache_data(show_spinner=False)
def fetch_full_document_text(urn, num_pages):
    full_doc_text = ""
    for page_number in range(1, num_pages + 1):
        alto_url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{urn}_{page_number:04d}"
        response = requests.get(alto_url)
        if response.status_code == 200:
            alto_xml = response.text
            _, _, _, _, _, page_text = parse_alto(alto_xml)
            if page_text:
                full_doc_text += f"=== Side {page_number} ===\n{page_text}\n\n"
        else:
            full_doc_text += f"=== Side {page_number} ===\n[FEIL: Kunne ikke hente tekst]\n\n"
    return full_doc_text.strip()


    
