# metadata_utils: fetch_iiif_manifest, get_page_list, get_metadata, extract_urn_or_lookup
from functools import lru_cache
import json
import re

import requests


@lru_cache(maxsize=128)
def fetch_iiif_manifest(urn):
    url = f"https://api.nb.no/catalog/v1/iiif/{urn}/manifest"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return None


def get_page_list(manifest):
    """Returns (labels, page_ids) where page_ids are extracted from IIIF canvas IDs."""
    if not manifest:
        return [], []
    try:
        canvases = manifest['sequences'][0]['canvases']
        labels = [f"Side {i+1}" for i in range(len(canvases))]
        page_ids = [c.get('@id', '').split('/canvas/')[-1] for c in canvases]
        return labels, page_ids
    except (KeyError, IndexError):
        return [], []


@lru_cache(maxsize=128)
def _fetch_metadata(urn):
    url = f"https://api.nb.no/catalog/v1/items/{urn}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return None


def get_metadata(urn):
    """Returns dict with title, year, urn — or None if unavailable."""
    data = _fetch_metadata(urn)
    if data is None:
        return None
    flat_json = json.dumps(data, ensure_ascii=False)
    title_match = re.search(r'"title"\s*:\s*"([^"]+?)"', flat_json)
    issued_match = re.search(r'"issued"\s*:\s*"(\d{4})"', flat_json)
    return {
        "title": title_match.group(1) if title_match else None,
        "year":  issued_match.group(1) if issued_match else None,
        "urn":   urn,
    }


def extract_urn_or_lookup(input_str):
    urn_match = re.search(r"URN:NBN:[^\s/?]+", input_str)
    if urn_match:
        return urn_match.group(0)

    id_match = re.search(r"/items/([a-f0-9]{32})", input_str)
    if id_match:
        doc_id = id_match.group(1)
        url = f"https://api.nb.no/catalog/v1/items/{doc_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                flat_json = json.dumps(response.json())
                urn_fallback = re.search(r"URN:NBN:[^\s\",]+", flat_json)
                if urn_fallback:
                    urn_cleaned = re.sub(r"_[^_]+/full/.*", "", urn_fallback.group(0))
                    urn_cleaned = re.sub(r"-\d+_\d+$", "", urn_cleaned)
                    return urn_cleaned
        except requests.RequestException:
            pass

    return None
