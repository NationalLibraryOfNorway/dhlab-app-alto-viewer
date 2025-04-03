# metadata_utils: fetch_iiif_manifest, get_page_list, show_metadata, extract_urn_or_lookup
import requests
import re
import streamlit as st
import json

def fetch_iiif_manifest(urn):
    url = f"https://api.nb.no/catalog/v1/iiif/{urn}/manifest"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Kunne ikke hente IIIF-manifestet. Status: {response.status_code}")
        return None

def get_page_list(manifest):
    if not manifest or 'sequences' not in manifest or not manifest['sequences'][0]['canvases']:
        return []
    return [f"Side {i+1}" for i in range(len(manifest['sequences'][0]['canvases']))]

def show_metadata(urn):
    url = f"https://api.nb.no/catalog/v1/items/{urn}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        flat_json = json.dumps(data, ensure_ascii=False)

        title_match = re.search(r'"title"\s*:\s*"([^"]+?)"', flat_json)
        issued_match = re.search(r'"issued"\s*:\s*"(\d{4})"', flat_json)

        title = title_match.group(1) if title_match else None
        year = issued_match.group(1) if issued_match else None

        with st.sidebar.expander("Vis metadata"):
            st.markdown(f"**Tittel:** {title}")
            st.markdown(f"**År:** {year}")
            st.markdown(f"**URN:** [nb.no/items/{urn}](https://www.nb.no/items/{urn})")
        
def extract_urn_or_lookup(input_str):
    urn_match = re.search(r"URN:NBN:[^\s/?]+", input_str)
    if urn_match:
        return urn_match.group(0)

    id_match = re.search(r"/items/([a-f0-9]{32})", input_str)
    if id_match:
        doc_id = id_match.group(1)
        url = f"https://api.nb.no/catalog/v1/items/{doc_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            flat_json = json.dumps(data)
            urn_fallback = re.search(r"URN:NBN:[^\s\",]+", flat_json)
            if urn_fallback:
                urn_cleaned = re.sub(r"_[^_]+/full/.*", "", urn_fallback.group(0))
                return urn_cleaned

    return None