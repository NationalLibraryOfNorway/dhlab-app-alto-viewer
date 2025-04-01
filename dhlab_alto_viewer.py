# Purpose: Streamlit app for viewing ALTO XML data from the National Library of Norway (NB) using IIIF URNs.
import streamlit as st
import requests
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO
from PIL import Image
import re

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

        import json
        flat_json = json.dumps(data, ensure_ascii=False)

        title_match = re.search(r'"title"\s*:\s*"([^"]+?)"', flat_json)
        issued_match = re.search(r'"issued"\s*:\s*"(\d{4})"', flat_json)

        title = title_match.group(1) if title_match else None
        year = issued_match.group(1) if issued_match else None

        st.sidebar.markdown("### Metadata:")
        if title:
            st.sidebar.markdown(f"**Tittel:** {title}")
        if year:
            st.sidebar.markdown(f"**År:** {year}")
        st.sidebar.markdown(f"**URN:** [nb.no/items/{urn}](https://www.nb.no/items/{urn})")
        
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
            import json
            flat_json = json.dumps(data)
            urn_fallback = re.search(r"URN:NBN:[^\s\",]+", flat_json)
            if urn_fallback:
                urn_cleaned = re.sub(r"_[^_]+/full/.*", "", urn_fallback.group(0))
                return urn_cleaned

    return None

def fetch_alto(urn, page):
    url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{urn}_{page:04d}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Kunne ikke hente ALTO XML for side {page}. Status: {response.status_code}")
        return None

def fetch_image(urn, page, scale=0.66):
    url = f"https://www.nb.no/services/image/resolver/{urn}_{page:04d}/full/pct:{int(scale * 100)}/0/native.jpg"
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(BytesIO(response.content))
    else:
        st.error(f"Kunne ikke hente bilde for side {page}. Status: {response.status_code}")
        return None

def parse_alto(alto_xml):
    root = ET.fromstring(alto_xml)
    ns = {"alto": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {"alto": ""}

    layout = root.find("alto:Layout", ns)
    if layout is None:
        st.error("Feil: Layout-element ikke funnet i ALTO XML")
        return None, None, [], [], [], ""

    page = layout.find("alto:Page", ns)
    if page is None:
        st.error("Feil: Page-element ikke funnet i ALTO XML")
        return None, None, [], [], [], ""

    width = int(page.attrib['WIDTH'])
    height = int(page.attrib['HEIGHT'])

    text_blocks = []
    lines = []
    words = []
    full_text = ""

    block_id = 1  # Felles løpenummer for blokker uansett hvor de ligger

    for area_tag, label in [("PrintSpace", "PrintSpace"), ("TopMargin", "TopMargin"), ("BottomMargin", "BottomMargin")]:
        area = page.find(f"alto:{area_tag}", ns)
        if area is None:
            continue
        for block in area.findall(".//alto:TextBlock", ns):
            x, y, w, h = (int(block.attrib['HPOS']), int(block.attrib['VPOS']),
                          int(block.attrib['WIDTH']), int(block.attrib['HEIGHT']))
            text_blocks.append((x, y, w, h, block_id, label))
            block_id += 1

            block_text = []
            for line in block.findall("alto:TextLine", ns):
                lx, ly, lw, lh = (int(line.attrib['HPOS']), int(line.attrib['VPOS']),
                                  int(line.attrib['WIDTH']), int(line.attrib['HEIGHT']))
                lines.append((lx, ly, lw, lh))

                line_text = []
                for string in line.findall("alto:String", ns):
                    wx, wy, ww, wh = (int(string.attrib['HPOS']), int(string.attrib['VPOS']),
                                      int(string.attrib['WIDTH']), int(string.attrib['HEIGHT']))
                    words.append((wx, wy, ww, wh))
                    line_text.append(string.attrib.get('CONTENT', ''))

                block_text.append(" ".join(line_text))

            full_text += "\n".join(block_text) + "\n\n"

    return width, height, text_blocks, lines, words, full_text.strip()


def plot_alto(image, alto_width, alto_height, elements, color="red", show_numbers=False):
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.imshow(image, cmap='gray')
    img_width, img_height = image.size
    scale_x = img_width / alto_width
    scale_y = img_height / alto_height

    for element in elements:
        # Håndter både 4-, 5- og 6-elementers tuples
        x, y, w, h = element[:4]
        num = element[4] if len(element) > 4 else None
        region = element[5] if len(element) > 5 else None

        # Velg farge ut fra region hvis tilgjengelig
        if region == "PrintSpace":
            edgecolor = "red"
            tag = None  # Ikke vis tag for PrintSpace
        elif region == "TopMargin":
            edgecolor = "orange"
            tag = "TopMargin"
        elif region == "BottomMargin":
            edgecolor = "gray"
            tag = "BottomMargin"
        else:
            edgecolor = color
            tag = None  # Ikke vis tag for linjer og ord

        # Tegn boksen
        rect = patches.Rectangle((x * scale_x, y * scale_y), w * scale_x, h * scale_y,
                                 linewidth=1, edgecolor=edgecolor, facecolor='none')
        ax.add_patch(rect)

        # Nummer i midten av boksen (valgfritt)
        if show_numbers and num is not None:
            ax.text((x + w / 2) * scale_x, (y + h / 2) * scale_y, str(num),
                    color='yellow', fontsize=10, ha='center', va='center',
                    bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))

        # Vis tag kun hvis definert
        if tag:
            ax.text(x * scale_x + 2, y * scale_y + 2, tag,
                    color=edgecolor, fontsize=8, ha='left', va='top',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.1'))

    ax.set_xticks([])
    ax.set_yticks([])
    st.pyplot(fig)

def main():
    st.set_page_config(layout="wide")
    st.title("ALTO-viewer for NB - fritt materiale")

    with st.sidebar:
        user_input = st.text_input("**Lim inn URN eller NB-lenke:**", "https://www.nb.no/items/URN:NBN:no-nb_digibok_2013122026001")
        urn = extract_urn_or_lookup(user_input)

        if urn:
            manifest = fetch_iiif_manifest(urn)
            pages = get_page_list(manifest)

            if pages:
                selected_page = st.selectbox("**Velg side:**", pages, index=0)
                page_number = pages.index(selected_page) + 1
            else:
                page_number = 1

            view_option = st.radio("**Visningsmodus**", ["Tekstblokker", "Linjer", "Ord"])
            st.sidebar.markdown('---')
            show_metadata(urn)
        else:
            page_number = None
            view_option = None
            st.warning("Fant ingen gyldig URN eller ID i inputen.")

    if urn and page_number and view_option:
        alto_xml = fetch_alto(urn, page_number)
        image = fetch_image(urn, page_number, scale=0.66)

        if alto_xml and image:
            alto_width, alto_height, text_blocks, lines, words, full_text = parse_alto(alto_xml)

            if alto_width and alto_height:
                if view_option == "Tekstblokker":
                    plot_alto(image, alto_width, alto_height, text_blocks, 'red', show_numbers=True)
                elif view_option == "Linjer":
                    plot_alto(image, alto_width, alto_height, lines, 'blue')
                elif view_option == "Ord":
                    plot_alto(image, alto_width, alto_height, words, 'green')

            if full_text:
                st.subheader("Transkribert tekst")
                st.text_area("", full_text, height=300)

                # Last ned tekst som txt
                st.download_button(
                    label="📥 Last ned tekst som .txt",
                    data=full_text,
                    file_name=f"{urn}_{page_number:04d}.txt",
                    mime="text/plain"
                )
                st.download_button(
                    label="📄 Last ned ALTO-XML",
                    data=alto_xml,
                    file_name=f"{urn}_{page_number:04d}.xml",
                    mime="application/xml"
                )

                image_url = f"https://www.nb.no/services/image/resolver/{urn}_{page_number:04d}/full/pct:100/0/native.jpg"
                alto_url= f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{urn}_{page_number:04d}"

                st.markdown(f'**Lenke til bilde:** <a heref="{image_url}" target="_blank">{image_url}</a>', unsafe_allow_html=True)
                st.markdown(f'**Lenke til ALTO-XML:** <a heref="{alto_url}" target="_blank">{alto_url}</a>', unsafe_allow_html=True)
                
if __name__ == '__main__':
    main()
