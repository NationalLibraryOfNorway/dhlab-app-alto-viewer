# fetch_image, plot_alto
import requests
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st

def fetch_image(urn, page, scale=0.5):
    url = f"https://www.nb.no/services/image/resolver/{urn}_{page:04d}/full/pct:{int(scale * 100)}/0/native.jpg"
    response = requests.get(url)
    if response.status_code == 200:
        return Image.open(BytesIO(response.content))
    else:
        st.error(f"Kunne ikke hente bilde for side {page}. Status: {response.status_code}")
        return None

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