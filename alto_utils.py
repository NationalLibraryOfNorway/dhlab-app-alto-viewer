# alto_utils: parse_alto, extract_ocr_info, extract_avg_wc
import xml.etree.ElementTree as ET


def parse_alto(alto_xml):
    if not alto_xml:
        return None, None, [], [], [], ""
    try:
        root = ET.fromstring(alto_xml)
    except ET.ParseError:
        return None, None, [], [], [], ""

    ns = {"alto": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {"alto": ""}

    layout = root.find("alto:Layout", ns)
    if layout is None:
        return None, None, [], [], [], ""

    page = layout.find("alto:Page", ns)
    if page is None:
        return None, None, [], [], [], ""

    try:
        width = int(page.attrib['WIDTH'])
        height = int(page.attrib['HEIGHT'])
    except (KeyError, ValueError):
        return None, None, [], [], [], ""

    # Noen ALTO-filer (f.eks. fra NB.no) har inkonsistente koordinatsystem der
    # TextBlock-koordinater bruker et stort ALTO-rom (f.eks. 3439×5063) mens
    # TextLine/String-koordinater bruker Page-dimensjonene (f.eks. 1289×2012).
    # Beregn det faktiske ALTO-rommet fra area-elementene, og normaliser
    # TextBlock-koordinater til Page-rommet. TextLine/String brukes uendret.
    alto_w, alto_h = width, height
    for area_tag in ["TopMargin", "BottomMargin", "PrintSpace", "LeftMargin", "RightMargin"]:
        area = page.find(f"alto:{area_tag}", ns)
        if area is not None:
            try:
                ax = int(area.attrib.get("HPOS", 0))
                ay = int(area.attrib.get("VPOS", 0))
                aw = int(area.attrib.get("WIDTH", 0))
                ah = int(area.attrib.get("HEIGHT", 0))
                alto_w = max(alto_w, ax + aw)
                alto_h = max(alto_h, ay + ah)
            except ValueError:
                pass
    block_scale_x = width / alto_w if alto_w > width * 1.1 else 1.0
    block_scale_y = height / alto_h if alto_h > height * 1.1 else 1.0

    text_blocks = []
    lines = []
    words = []
    full_text = ""

    block_id = 1

    for area_tag, label in [("PrintSpace", "PrintSpace"), ("TopMargin", "TopMargin"), ("BottomMargin", "BottomMargin")]:
        area = page.find(f"alto:{area_tag}", ns)
        if area is None:
            continue
        for block in area.findall(".//alto:TextBlock", ns):
            try:
                x, y, w, h = (int(block.attrib.get('HPOS', 0)), int(block.attrib.get('VPOS', 0)),
                              int(block.attrib.get('WIDTH', 0)), int(block.attrib.get('HEIGHT', 0)))
            except ValueError:
                continue
            bx = round(x * block_scale_x)
            by = round(y * block_scale_y)
            bw = round(w * block_scale_x)
            bh = round(h * block_scale_y)
            text_blocks.append((bx, by, bw, bh, block_id, label))
            block_id += 1

            block_text = []
            for line in block.findall("alto:TextLine", ns):
                try:
                    lx, ly, lw, lh = (int(line.attrib.get('HPOS', 0)), int(line.attrib.get('VPOS', 0)),
                                      int(line.attrib.get('WIDTH', 0)), int(line.attrib.get('HEIGHT', 0)))
                except ValueError:
                    continue
                lines.append((lx, ly, lw, lh))

                line_text = []
                for string in line.findall("alto:String", ns):
                    try:
                        wx, wy, ww, wh = (int(string.attrib.get('HPOS', 0)), int(string.attrib.get('VPOS', 0)),
                                          int(string.attrib.get('WIDTH', 0)), int(string.attrib.get('HEIGHT', 0)))
                    except ValueError:
                        continue
                    words.append((wx, wy, ww, wh))
                    line_text.append(string.attrib.get('CONTENT', ''))

                block_text.append(" ".join(line_text))

            full_text += "\n".join(block_text) + "\n\n"

    return width, height, text_blocks, lines, words, full_text.strip()


def extract_ocr_info(alto_xml):
    if not alto_xml:
        return []
    try:
        root = ET.fromstring(alto_xml)
    except ET.ParseError:
        return []
    info = []

    description = next((child for child in root if child.tag.endswith("Description")), None)
    if description is None:
        return []

    for ocr_proc in description:
        if not ocr_proc.tag.endswith("OCRProcessing"):
            continue
        for step in ocr_proc:
            if not step.tag.lower().endswith("step"):
                continue
            label = "OCR-prosessering" if "ocr" in step.tag.lower() else "Preprosessering:"
            for child in step:
                if child.tag.endswith("processingSoftware"):
                    name = creator = version = None
                    for element in child:
                        tag = element.tag.split("}")[-1]
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
                    break
    return info


def extract_avg_wc(alto_xml):
    if not alto_xml:
        return None
    try:
        root = ET.fromstring(alto_xml)
    except ET.ParseError:
        return None
    wc_values = []
    for word in root.findall(".//String"):
        wc_str = word.attrib.get("WC")
        if wc_str:
            try:
                wc_values.append(float(wc_str))
            except ValueError:
                pass
    return round(sum(wc_values) / len(wc_values), 3) if wc_values else None
