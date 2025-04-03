#alto_utils: parse_alto, extract_ocr_info, extract_avg_wc
import xml.etree.ElementTree as ET
import streamlit as st  

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

def extract_ocr_info(alto_xml):
    root = ET.fromstring(alto_xml)
    info = []

    # Finn <Description>
    description = next((child for child in root if child.tag.endswith("Description")), None)
    if description is None:
        return []

    # Gå gjennom alle <OCRProcessing>-blokker
    for ocr_proc in description:
        if not ocr_proc.tag.endswith("OCRProcessing"):
            continue

        for step in ocr_proc:
            if not step.tag.lower().endswith("step"):
                continue

            label = "OCR-prosessering" if "ocr" in step.tag.lower() else "Preprosessering:"

            # Gå gjennom alle barna og let etter processingSoftware manuelt
            for child in step:
                if child.tag.endswith("processingSoftware"):
                    name = None
                    creator = None
                    version = None

                    for element in child:
                        tag = element.tag.split("}")[-1]  # fjern namespace
                        text = element.text.strip() if element.text else ""
                        if tag == "softwareName":
                            name = text
                        elif tag == "softwareCreator":
                            creator = text
                        elif tag == "softwareVersion":
                            version = text

                    parts = [f"**{label}**: {name or '(ukjent)'}"]
                    if version:
                        parts.append(f"versjon {version}")
                    if creator:
                        parts.append(f"({creator})")

                    info.append(" ".join(parts))
                    break  # slutt etter første processingSoftware

    return info

def extract_avg_wc(alto_xml):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(alto_xml)
    wc_values = []
    for word in root.findall(".//String"):
        wc_str = word.attrib.get("WC")
        if wc_str:
            try:
                wc_values.append(float(wc_str))
            except ValueError:
                pass
    return round(sum(wc_values) / len(wc_values), 3) if wc_values else None