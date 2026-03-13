# download_utils: fetch_alto, fetch_full_document_text
import requests
import streamlit as st
from alto_utils import parse_alto


@st.cache_data(show_spinner=False)
def fetch_alto(urn, page_id, page_number):
    url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{page_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
        if response.status_code in (404, 500):
            st.info(f"Ingen ALTO-data tilgjengelig for side {page_number}.")
        else:
            st.warning(f"Kunne ikke hente ALTO XML for side {page_number}. Status: {response.status_code}")
    except requests.RequestException as e:
        st.error(f"Nettverksfeil ved henting av ALTO XML: {e}")
    return None
    
@st.cache_data(show_spinner=False)
def fetch_full_document_text(urn, page_ids):
    full_doc_text = ""
    for page_number, page_id in enumerate(page_ids, 1):
        alto_url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{page_id}"
        try:
            response = requests.get(alto_url, timeout=10)
            if response.status_code == 200:
                alto_xml = response.text
                _, _, _, _, _, page_text = parse_alto(alto_xml)
                if page_text:
                    full_doc_text += f"=== Side {page_number} ===\n{page_text}\n\n"
            elif response.status_code not in (404, 500):
                full_doc_text += f"=== Side {page_number} ===\n[FEIL: Status {response.status_code}]\n\n"
        except requests.RequestException:
            full_doc_text += f"=== Side {page_number} ===\n[FEIL: Nettverksfeil]\n\n"
    return full_doc_text.strip()


    
