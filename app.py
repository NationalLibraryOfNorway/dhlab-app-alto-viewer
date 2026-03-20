import json
import re

import requests
from flask import Flask, Blueprint, render_template, request, jsonify, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from alto_utils import parse_alto, extract_avg_wc, extract_ocr_info
from image_utils import fetch_image, plot_alto
from download_utils import fetch_alto
from metadata_utils import fetch_iiif_manifest, get_page_list, get_metadata, extract_urn_or_lookup

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://",
)

bp = Blueprint('alto_viewer', __name__)

# Valideringsmønstre
_URN_RE     = re.compile(r'^URN:NBN:no-nb_[A-Za-z0-9_\-]+$', re.IGNORECASE)
_PAGE_ID_RE = re.compile(r'^[A-Za-z0-9:_\-]+$')


def _valid_urn(s):
    return bool(_URN_RE.match(s))


def _valid_page_id(s):
    return bool(_PAGE_ID_RE.match(s))


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/api/pages')
def api_pages():
    input_str = request.args.get('input', '').strip()
    if not input_str:
        return jsonify({'error': 'Tomt søkefelt'}), 400

    urn = extract_urn_or_lookup(input_str)
    if not urn:
        return jsonify({'error': 'Ugyldig URN eller lenke'}), 400

    if not _valid_urn(urn):
        return jsonify({'error': 'Ugyldig URN-format'}), 400

    manifest = fetch_iiif_manifest(urn)
    if not manifest:
        return jsonify({'error': 'Kunne ikke hente IIIF-manifest'}), 502

    labels, page_ids = get_page_list(manifest)
    if not labels:
        return jsonify({'error': 'Ingen sider funnet for dette dokumentet'}), 404

    pages = [{'label': l, 'page_id': p} for l, p in zip(labels, page_ids)]
    return jsonify({'urn': urn, 'pages': pages})


@bp.route('/api/render')
def api_render():
    urn     = request.args.get('urn', '').strip()
    page_id = request.args.get('page_id', '').strip()
    view    = request.args.get('view', 'tekstblokker').strip()

    if not urn or not page_id:
        return jsonify({'error': 'Mangler urn eller page_id'}), 400

    if not _valid_urn(urn):
        return jsonify({'error': 'Ugyldig URN-format'}), 400

    if not _valid_page_id(page_id):
        return jsonify({'error': 'Ugyldig side-ID'}), 400

    alto_xml = fetch_alto(urn, page_id)
    image    = fetch_image(page_id)

    width, height, text_blocks, lines, words, full_text = parse_alto(alto_xml)
    avg_wc   = extract_avg_wc(alto_xml)
    ocr_info = extract_ocr_info(alto_xml)
    metadata = get_metadata(urn)

    view_map = {
        'tekstblokker': (text_blocks, 'red',   True),
        'tekstlinjer':  (lines,       'blue',  False),
        'ord':          (words,       'green', False),
    }
    elements, color, show_numbers = view_map.get(view, (text_blocks, 'red', True))
    image_b64 = plot_alto(image, width, height, elements, color=color, show_numbers=show_numbers)

    return jsonify({
        'image_b64': image_b64,
        'full_text': full_text,
        'metadata':  metadata,
        'ocr_info':  ocr_info,
        'avg_wc':    avg_wc,
        'links': {
            'image': f"https://www.nb.no/services/image/resolver/{page_id}/full/pct:66/0/native.jpg",
            'alto':  f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{page_id}",
        },
    })


@bp.route('/api/download/page')
def download_page():
    urn     = request.args.get('urn', '').strip()
    page_id = request.args.get('page_id', '').strip()

    if not _valid_urn(urn):
        return jsonify({'error': 'Ugyldig URN-format'}), 400

    if not _valid_page_id(page_id):
        return jsonify({'error': 'Ugyldig side-ID'}), 400

    alto_xml = fetch_alto(urn, page_id)
    _, _, _, _, _, full_text = parse_alto(alto_xml)
    return Response(
        full_text or '',
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{page_id}.txt"'},
    )


@bp.route('/api/download/full/progress')
@limiter.limit("5 per hour")
def download_full_progress():
    urn          = request.args.get('urn', '').strip()
    page_ids_str = request.args.get('page_ids', '').strip()

    if not _valid_urn(urn):
        return jsonify({'error': 'Ugyldig URN-format'}), 400

    page_ids = [p for p in page_ids_str.split(',') if p and _valid_page_id(p)]
    total    = len(page_ids)

    def generate():
        full_text = ""
        for i, page_id in enumerate(page_ids, 1):
            url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{page_id}"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    _, _, _, _, _, page_text = parse_alto(resp.text)
                    if page_text:
                        full_text += f"=== Side {i} ===\n{page_text}\n\n"
                elif resp.status_code not in (404, 500):
                    full_text += f"=== Side {i} ===\n[FEIL: Status {resp.status_code}]\n\n"
            except requests.RequestException:
                full_text += f"=== Side {i} ===\n[FEIL: Nettverksfeil]\n\n"

            yield f"data: {json.dumps({'current': i, 'total': total, 'done': False})}\n\n"

        yield f"data: {json.dumps({'current': total, 'total': total, 'done': True, 'text': full_text.strip()})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


app.register_blueprint(bp, url_prefix='/alto-viewer')

if __name__ == '__main__':
    app.run(debug=True)
