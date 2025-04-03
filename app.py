import streamlit as st


from alto_utils import parse_alto, extract_avg_wc, extract_ocr_info
from image_utils import fetch_image, plot_alto
from metadata_utils import extract_urn_or_lookup, fetch_iiif_manifest, get_page_list, show_metadata
from download_utils import fetch_alto, fetch_full_document_text



def main():
    st.title("ALTO-visning for dokumenter fra nb.no")

    with st.sidebar:
        user_input = st.text_input(
            "Lim inn URN eller lenke til dokument",
            value="URN:NBN:no-nb_digibok_2016040508078"
        )
        urn = extract_urn_or_lookup(user_input)

        if urn:
            manifest = fetch_iiif_manifest(urn)
            pages = get_page_list(manifest)

            if "page_number" not in st.session_state:
                st.session_state.page_number = 1

            selected_page = st.selectbox("Velg side:", pages, index=st.session_state.page_number - 1)
            st.session_state.page_number = pages.index(selected_page) + 1
            page_number = st.session_state.page_number

            view_option = st.radio(
                "Vis",
                options=["Tekstblokker", "Tekstlinjer", "Ord"],
                horizontal=False
            )

            alto_xml = fetch_alto(urn, page_number)
            avg_wc = extract_avg_wc(alto_xml)
            image = fetch_image(urn, page_number)
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

            image_url = f"https://www.nb.no/services/image/resolver/{urn}_{page_number:04d}/full/pct:66/0/native.jpg"
            alto_url = f"https://api.nb.no/catalog/v1/metadata/{urn}/altos/{urn}_{page_number:04d}"
            with st.sidebar.expander("Lenker for denne siden"):
                st.markdown(f"[Bilde (IIIF)]({image_url})")
                st.markdown(f"[ALTO XML]({alto_url})")

            with st.sidebar.expander("Nedlastinger"):
                st.download_button(
                    label="📥 Last ned denne siden (.txt)",
                    data=full_text,
                    file_name=f"{urn}_{page_number:04d}.txt",
                    mime="text/plain"
                )

                if st.button("📘 Last ned hele dokumentet (.txt)"):
                    with st.spinner("Henter og samler tekst fra alle sider..."):
                        full_doc_text = fetch_full_document_text(urn, len(pages))
                    st.download_button(
                        label="⬇️ Klikk her for å laste ned hele dokumentet",
                        data=full_doc_text,
                        file_name=f"{urn}_FULLTEKST.txt",
                        mime="text/plain"
                    )

    if urn:
        if image:
            with st.spinner("Laster bilde og tekst..."):
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