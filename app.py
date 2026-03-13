import base64
import streamlit as st

from alto_utils import parse_alto, extract_avg_wc, extract_ocr_info
from image_utils import fetch_image, plot_alto
from metadata_utils import extract_urn_or_lookup, fetch_iiif_manifest, get_page_list, show_metadata
from download_utils import fetch_alto, fetch_full_document_text


def _svg_b64():
    try:
        with open("favicon.svg", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""


def main():
    svg_b64 = _svg_b64()

    st.set_page_config(
        page_title="DH-LAB | ALTO-visning",
        page_icon=f"data:image/svg+xml;base64,{svg_b64}" if svg_b64 else "📄",
        layout="centered",
    )

    st.markdown(f"""
    <style>
    /* Fonter */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600&display=swap');
    :root {{
        --mono: 'IBM Plex Mono', ui-monospace, monospace;
        --sans: 'IBM Plex Sans', system-ui, sans-serif;
    }}
    html, body, .stApp, p, label {{
        font-family: var(--sans);
    }}
    h1 {{
        font-family: var(--mono);
        font-weight: 700;
        color: #40263E;
    }}
    h2, h3 {{
        font-family: var(--mono);
    }}
/* Knapper */
    .stButton > button {{
        background-color: #40263E;
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
    }}
    .stButton > button:hover {{
        background-color: #1A1A1A;
        color: #FFFFFF;
        border: none;
    }}
    .stButton > button:disabled {{
        background-color: #E0E0E0;
        color: #1A1A1A66;
        border: none;
    }}
    /* Nedlastingsknapp */
    .stDownloadButton > button {{
        background-color: #40263E;
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
    }}
    .stDownloadButton > button:hover {{
        background-color: #40263E;
        color: #FFFFFF;
        border: none;
    }}
    /* Ekspandere */
    details summary {{
        color: #550029;
        font-weight: 600;
    }}
    /* Lenker */
    a {{
        color: #40263E !important;
    }}
    a:hover {{
        color: #1A1A1A !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.title("ALTO-visning")
    st.markdown("Visualiser layout og hent ut tekst fra dokumenter på nb.no.")

    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 1.5rem 0 2rem 0; border-bottom: 1px solid #E0E0E0; margin-bottom: 1.5rem;">
            <a href="https://dh.nb.no" target="_blank" style="text-decoration: none; color: inherit;">
                <img src="data:image/svg+xml;base64,{svg_b64}" height="32" alt="DH-LAB logo" style="margin-bottom: 0.5rem; display: block;">
                <div style="font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 15px; color: #1A1A1A; line-height: 1.3;">DH-LAB</div>
                <div style="font-family: 'IBM Plex Sans', sans-serif; font-size: 12px; color: #1A1A1A99; line-height: 1.3;">Nasjonalbiblioteket</div>
            </a>
        </div>
        """, unsafe_allow_html=True)

        user_input = st.text_input(
            "Lim inn URN eller lenke til dokument",
            value="URN:NBN:no-nb_digibok_2016040508078"
        )
        urn = extract_urn_or_lookup(user_input)

        if urn:
            manifest = fetch_iiif_manifest(urn)
            pages, page_ids = get_page_list(manifest)

            if not pages:
                st.warning("Ingen sider funnet for dette dokumentet.")
                st.stop()

            if "page_number" not in st.session_state:
                st.session_state.page_number = 1

            st.session_state.page_number = min(st.session_state.page_number, len(pages))
            page_number = st.session_state.page_number

            def go_prev():
                st.session_state.page_number = max(1, st.session_state.page_number - 1)

            def go_next():
                st.session_state.page_number = min(len(pages), st.session_state.page_number + 1)

            col1, col2, col3 = st.columns([1, 5, 1])
            with col1:
                st.button("◀", on_click=go_prev, disabled=(page_number <= 1))
            with col2:
                selected_page = st.selectbox(
                    "Velg side:", pages,
                    index=page_number - 1,
                    label_visibility="collapsed"
                )
            with col3:
                st.button("▶", on_click=go_next, disabled=(page_number >= len(pages)))

            st.session_state.page_number = pages.index(selected_page) + 1
            page_number = st.session_state.page_number
            page_id = page_ids[page_number - 1]

            view_option = st.radio(
                "Vis",
                options=["Tekstblokker", "Tekstlinjer", "Ord"],
                horizontal=False
            )

            with st.spinner("Henter side..."):
                alto_xml = fetch_alto(urn, page_id, page_number)
                image = fetch_image(page_id, page_number)

            avg_wc = extract_avg_wc(alto_xml)
            width, height, text_blocks, lines, words, full_text = parse_alto(alto_xml)

            show_metadata(urn)

            ocr_info = extract_ocr_info(alto_xml)
            if ocr_info or avg_wc is not None:
                with st.sidebar.expander("OCR-informasjon"):
                    if ocr_info:
                        for line in ocr_info:
                            st.markdown(f"{line}")
                    if avg_wc is not None:
                        st.markdown(f"**Word Confidence:** {avg_wc}")

            image_url = f"https://www.nb.no/services/image/resolver/{page_id}/full/pct:66/0/native.jpg"
            alto_url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{page_id}"
            with st.sidebar.expander("Lenker for denne siden"):
                st.markdown(f"[Bilde (IIIF)]({image_url})")
                st.markdown(f"[ALTO XML]({alto_url})")

            with st.sidebar.expander("Nedlastinger"):
                st.download_button(
                    label="📥 Last ned denne siden (.txt)",
                    data=full_text,
                    file_name=f"{page_id}.txt",
                    mime="text/plain"
                )

                if st.button("📘 Last ned hele dokumentet (.txt)"):
                    with st.spinner("Henter og samler tekst fra alle sider..."):
                        full_doc_text = fetch_full_document_text(urn, tuple(page_ids))
                    st.download_button(
                        label="⬇️ Klikk her for å laste ned hele dokumentet",
                        data=full_doc_text,
                        file_name=f"{urn}_FULLTEKST.txt",
                        mime="text/plain"
                    )

    if urn:
        if image and width is not None and height is not None:
            with st.spinner("Tegner overlay..."):
                if view_option == "Tekstblokker":
                    plot_alto(image, width, height, text_blocks, color="red", show_numbers=True)
                elif view_option == "Tekstlinjer":
                    plot_alto(image, width, height, lines, color="blue", show_numbers=False)
                elif view_option == "Ord":
                    plot_alto(image, width, height, words, color="green", show_numbers=False)

        if full_text:
            st.text_area("Transkribert tekst", full_text, height=300)
        else:
            st.info("Ingen transkribert tekst tilgjengelig for denne siden.")


if __name__ == '__main__':
    main()
