# image_utils: fetch_image, plot_alto
import io
import base64
from functools import lru_cache

import requests
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches


@lru_cache(maxsize=64)
def fetch_image(page_id, scale=0.5):
    url = f"https://www.nb.no/services/image/resolver/{page_id}/full/pct:{int(scale * 100)}/0/native.jpg"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
    except requests.RequestException:
        pass
    return None


def plot_alto(image, alto_width, alto_height, elements, color="red", show_numbers=False):
    """Render ALTO overlay on image and return a base64-encoded PNG string."""
    if image is None or alto_width is None or alto_height is None:
        return None

    fig, ax = plt.subplots(figsize=(10, 12))
    ax.imshow(image, cmap='gray')
    img_width, img_height = image.size
    scale_x = img_width / alto_width
    scale_y = img_height / alto_height

    for element in elements:
        x, y, w, h = element[:4]
        num = element[4] if len(element) > 4 else None
        region = element[5] if len(element) > 5 else None

        if region == "PrintSpace":
            edgecolor = "red"
            tag = None
        elif region == "TopMargin":
            edgecolor = "orange"
            tag = "TopMargin"
        elif region == "BottomMargin":
            edgecolor = "gray"
            tag = "BottomMargin"
        else:
            edgecolor = color
            tag = None

        rect = patches.Rectangle(
            (x * scale_x, y * scale_y), w * scale_x, h * scale_y,
            linewidth=1, edgecolor=edgecolor, facecolor='none'
        )
        ax.add_patch(rect)

        if show_numbers and num is not None:
            ax.text(
                (x + w / 2) * scale_x, (y + h / 2) * scale_y, str(num),
                color='yellow', fontsize=10, ha='center', va='center',
                bbox=dict(facecolor='black', alpha=0.5, edgecolor='none')
            )

        if tag:
            ax.text(
                x * scale_x + 2, y * scale_y + 2, tag,
                color=edgecolor, fontsize=8, ha='left', va='top',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.1')
            )

    ax.set_xticks([])
    ax.set_yticks([])

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
