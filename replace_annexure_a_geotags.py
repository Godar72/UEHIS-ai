"""
Replace Appendix A with authentic Geotag Photos in UEHIS_Service_Learning_Report_Aditya_Godar.docx.
Ensures:
- Page 56: Level 1 Heading, Intro, 2x2 grid of Figures 50, 51, 52, 53 with captions (no page spillover).
- Page 57: 1x2 grid of Figures 54, 55 with captions.
- Table of Contents synchronized (Page 56).
- List of Figures synchronized (Figures 50-53 on Page 56, Figures 54-55 on Page 57).
- Total document pages = exactly 57 pages.
"""

import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

DOCX_PATH = "UEHIS_Service_Learning_Report_Aditya_Godar.docx"
BACKUP_PATH = "UEHIS_Service_Learning_Report_Aditya_Godar_before_geotags.docx"

COLOR_NAVY = RGBColor(23, 43, 92)       # #172B5C
COLOR_DARK_TEXT = RGBColor(30, 41, 59)  # #1E293B
COLOR_MUTED = RGBColor(100, 116, 139)   # #64748B

GEOTAG_CONFIGS = [
    {
        "fig_num": 50,
        "img_path": "report_figures/fig50_geotag.jpeg",
        "lof_title": "Project Initiation & Team Orientation at SEER Bharat Foundation Office (5th July 2026)",
        "caption": "Project initiation & institutional orientation with the UEHIS team at SEER Bharat Foundation office, Wakad (05/07/2026, 04:30 PM, Lat 18.598544, Long 73.768224).",
        "page": "56"
    },
    {
        "fig_num": 51,
        "img_path": "report_figures/fig51_geotag.jpeg",
        "lof_title": "Community Sapling Plantation & Root-Bed Soil Preparation (18th September 2026)",
        "caption": "Community afforestation drive: Sapling plantation and root-bed soil preparation at Godrej Green Vistas, Pune (18/09/2026, 04:04 PM, Lat 18.566264, Long 73.737152).",
        "page": "56"
    },
    {
        "fig_num": 52,
        "img_path": "report_figures/fig52_geotag.jpeg",
        "lof_title": "Community Ecological Awareness & Leaflet Distribution Outreach (18th September 2026)",
        "caption": "Community ecological awareness campaign: Distribution of SEER Bharat afforestation leaflets (18/09/2026, 04:08 PM, Lat 18.566343, Long 73.736992).",
        "page": "56"
    },
    {
        "fig_num": 53,
        "img_path": "report_figures/fig53_geotag.jpeg",
        "lof_title": "Collaborative Machine Learning & U-Net Inference Validation Session (27th September 2026)",
        "caption": "Collaborative machine learning session: Validating U-Net geospatial inference model outputs on laptops (27/09/2026, 12:03 PM, Lat 18.598440, Long 73.768398).",
        "page": "56"
    },
    {
        "fig_num": 54,
        "img_path": "report_figures/fig54_geotag.jpeg",
        "lof_title": "Technical Review & UEHIS Platform Demonstration with Project Mentor (27th September 2026)",
        "caption": "Technical review and architecture demonstration of the UEHIS decision-support platform with project mentor (27/09/2026, 12:09 PM, Lat 18.598470, Long 73.768243).",
        "page": "57"
    },
    {
        "fig_num": 55,
        "img_path": "report_figures/fig55_geotag.jpeg",
        "lof_title": "Final Documentation Verification & Sign-Off with Director Prof. Darshan Talhande (16th October 2026)",
        "caption": "Final documentation audit, completion verification, and institutional sign-off with Director Prof. Darshan Talhande (16/10/2026, 08:46 PM, Lat 18.598262, Long 73.768336).",
        "page": "57"
    }
]

def set_cell_margins(cell, top=15, bottom=15, left=10, right=10):
    """Set cell padding in twips."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_cell_borders(cell, top="none", bottom="none", left="none", right="none"):
    """Set custom borders on a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders_xml = f'<w:tcBorders {nsdecls("w")}>'
    for side, val in [("top", top), ("left", left), ("bottom", bottom), ("right", right)]:
        borders_xml += f'<w:{side} w:val="{val}"/>'
    borders_xml += '</w:tcBorders>'
    tcPr.append(parse_xml(borders_xml))

def format_caption(cell, fig_num, caption_text):
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.02
    
    r_fig = p.add_run(f"Figure {fig_num}. ")
    r_fig.font.name = 'Times New Roman'
    r_fig.font.size = Pt(8.5)
    r_fig.font.bold = True
    r_fig.font.color.rgb = COLOR_NAVY
    
    r_cap = p.add_run(caption_text)
    r_cap.font.name = 'Times New Roman'
    r_cap.font.size = Pt(8.5)
    r_cap.font.color.rgb = COLOR_DARK_TEXT

def place_image_in_cell(cell, img_path, width_in=2.05):
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(1)
    run = p.add_run()
    run.add_picture(img_path, width=Inches(width_in))

def main():
    print(f"Loading {DOCX_PATH}...")
    doc = docx.Document(DOCX_PATH)

    # 1. Update Table of Contents (P107)
    for p in doc.paragraphs:
        if "Appendix A:" in p.text and ("55" in p.text or "56" in p.text):
            print("Updating Table of Contents entry for Appendix A...")
            p.text = "Appendix A: All Geotag Photos ........................................................ 56"
            p.runs[0].font.name = 'Times New Roman'
            p.runs[0].font.size = Pt(10.5)
            p.runs[0].font.color.rgb = COLOR_DARK_TEXT
            break

    # 2. Update List of Figures (Figures 50-55)
    lof_indices = []
    for idx, p in enumerate(doc.paragraphs):
        if "Figure 50." in p.text and "Progress Confirmation Letter" in p.text:
            lof_indices.append(idx)
        elif "Figure 51." in p.text and "Progress Confirmation Letter" in p.text:
            lof_indices.append(idx)

    if len(lof_indices) == 2:
        print(f"Found LOF Figure 50 at P{lof_indices[0]} and Figure 51 at P{lof_indices[1]}")
        p50 = doc.paragraphs[lof_indices[0]]
        p51 = doc.paragraphs[lof_indices[1]]
        
        # Replace p50 with Fig 50
        p50.clear()
        r50_1 = p50.add_run(f"Figure 50.  {GEOTAG_CONFIGS[0]['lof_title']}")
        r50_1.font.name = 'Times New Roman'
        r50_1.font.size = Pt(9.0)
        r50_1.font.color.rgb = COLOR_DARK_TEXT
        r50_2 = p50.add_run(f" .. {GEOTAG_CONFIGS[0]['page']}")
        r50_2.font.name = 'Times New Roman'
        r50_2.font.size = Pt(9.0)
        r50_2.font.color.rgb = COLOR_MUTED

        # Replace p51 with Fig 51
        p51.clear()
        r51_1 = p51.add_run(f"Figure 51.  {GEOTAG_CONFIGS[1]['lof_title']}")
        r51_1.font.name = 'Times New Roman'
        r51_1.font.size = Pt(9.0)
        r51_1.font.color.rgb = COLOR_DARK_TEXT
        r51_2 = p51.add_run(f" .. {GEOTAG_CONFIGS[1]['page']}")
        r51_2.font.name = 'Times New Roman'
        r51_2.font.size = Pt(9.0)
        r51_2.font.color.rgb = COLOR_MUTED

        # Add Figs 52, 53, 54, 55 right after p51
        curr = p51._element
        for cfg in GEOTAG_CONFIGS[2:]:
            new_p = doc.add_paragraph()
            new_p.paragraph_format.space_before = Pt(0)
            new_p.paragraph_format.space_after = Pt(2)
            new_p.paragraph_format.line_spacing = 1.05
            r1 = new_p.add_run(f"Figure {cfg['fig_num']}.  {cfg['lof_title']}")
            r1.font.name = 'Times New Roman'
            r1.font.size = Pt(9.0)
            r1.font.color.rgb = COLOR_DARK_TEXT
            r2 = new_p.add_run(f" .. {cfg['page']}")
            r2.font.name = 'Times New Roman'
            r2.font.size = Pt(9.0)
            r2.font.color.rgb = COLOR_MUTED
            
            curr.addnext(new_p._element)
            curr = new_p._element
        print("List of Figures updated with Figures 50-55!")

    # 3. Update Section 9 reference text
    for p in doc.paragraphs:
        if "Scanned photographic evidence of institutional progress documentation is provided in Appendix A" in p.text:
            print("Updating Section 9 reference text...")
            p.text = p.text.replace(
                "Scanned photographic evidence of institutional progress documentation is provided in Appendix A (Figures 50 and 51).",
                "Comprehensive photographic evidence with authentic GPS Map Camera geotags and timestamps documenting institutional progress, on-site activities, community afforestation, and final sign-off is provided in Appendix A (Figures 50 to 55)."
            )
            break

    # 4. Find the ACTUAL Appendix A heading at the end of the body (search backwards from end)
    body = doc._body._element
    real_app_idx = None
    for idx in range(len(body) - 1, 0, -1):
        child = body[idx]
        text = ''.join(child.itertext())
        if "Appendix A:" in text:
            real_app_idx = idx
            break

    if real_app_idx is None or real_app_idx < 400:
        raise ValueError(f"Could not locate actual Appendix A heading at the end of body! Found idx={real_app_idx}")

    break_idx = real_app_idx - 1
    p_break_before_app = body[break_idx]
    print(f"Actual Appendix A starts at body index {real_app_idx}, preceded by page break at index {break_idx}")

    # Remove all elements from real_app_idx up to sectPr
    elems_to_remove = []
    for idx in range(real_app_idx, len(body)):
        tag = body[idx].tag.split('}')[-1]
        if tag == 'sectPr':
            break
        elems_to_remove.append(body[idx])

    print(f"Removing {len(elems_to_remove)} existing Appendix A body elements...")
    for elem in elems_to_remove:
        elem.getparent().remove(elem)

    # 5. Build new Appendix A elements
    print("Building new Appendix A with Geotag Photos...")
    
    # Heading
    h_app = doc.add_paragraph()
    h_app.paragraph_format.keep_with_next = True
    h_app.paragraph_format.space_before = Pt(10)
    h_app.paragraph_format.space_after = Pt(4)
    h_app.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_h = h_app.add_run("Appendix A: All Geotag Photos")
    r_h.font.name = 'Times New Roman'
    r_h.font.size = Pt(14)
    r_h.font.bold = True
    r_h.font.color.rgb = COLOR_NAVY

    # Intro paragraph
    p_intro = doc.add_paragraph()
    p_intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_intro.paragraph_format.space_before = Pt(0)
    p_intro.paragraph_format.space_after = Pt(4)
    p_intro.paragraph_format.line_spacing = 1.15
    r_intro = p_intro.add_run(
        "All geotag photos from progress reports, on-site activities, community afforestation drives, and technical review sessions "
        "with SEER Bharat Foundation, presented in chronological date order with authentic GPS Map Camera location coordinates, address, and timestamp verification."
    )
    r_intro.font.name = 'Times New Roman'
    r_intro.font.size = Pt(10.5)
    r_intro.font.color.rgb = COLOR_DARK_TEXT

    # Table 1: Page 56 (Figures 50, 51, 52, 53) -> width 2.05 in, height 2.73 in
    col_widths = [Inches(3.1), Inches(0.3), Inches(3.1)]
    tbl1 = doc.add_table(rows=4, cols=3)
    tbl1.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl1.autofit = False
    for row in tbl1.rows:
        row._tr.get_or_add_trPr().append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        for c_idx, w in enumerate(col_widths):
            cell = row.cells[c_idx]
            cell.width = w
            set_cell_borders(cell, top="none", bottom="none", left="none", right="none")
            set_cell_margins(cell, top=15, bottom=15, left=10, right=10)

    # Row 0: Fig 50 & Fig 51 Images
    place_image_in_cell(tbl1.cell(0, 0), GEOTAG_CONFIGS[0]["img_path"], width_in=2.05)
    place_image_in_cell(tbl1.cell(0, 2), GEOTAG_CONFIGS[1]["img_path"], width_in=2.05)

    # Row 1: Fig 50 & Fig 51 Captions
    format_caption(tbl1.cell(1, 0), 50, GEOTAG_CONFIGS[0]["caption"])
    format_caption(tbl1.cell(1, 2), 51, GEOTAG_CONFIGS[1]["caption"])

    # Row 2: Fig 52 & Fig 53 Images
    place_image_in_cell(tbl1.cell(2, 0), GEOTAG_CONFIGS[2]["img_path"], width_in=2.05)
    place_image_in_cell(tbl1.cell(2, 2), GEOTAG_CONFIGS[3]["img_path"], width_in=2.05)

    # Row 3: Fig 52 & Fig 53 Captions
    format_caption(tbl1.cell(3, 0), 52, GEOTAG_CONFIGS[2]["caption"])
    format_caption(tbl1.cell(3, 2), 53, GEOTAG_CONFIGS[3]["caption"])

    # Hard Page Break to Page 57
    p_page_break = doc.add_paragraph()
    r_pb = p_page_break.add_run()
    r_pb.add_break(docx.enum.text.WD_BREAK.PAGE)

    # Table 2: Page 57 (Figures 54, 55) -> width 2.45 in
    tbl2 = doc.add_table(rows=2, cols=3)
    tbl2.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl2.autofit = False
    for row in tbl2.rows:
        row._tr.get_or_add_trPr().append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        for c_idx, w in enumerate(col_widths):
            cell = row.cells[c_idx]
            cell.width = w
            set_cell_borders(cell, top="none", bottom="none", left="none", right="none")
            set_cell_margins(cell, top=30, bottom=30, left=15, right=15)

    # Row 0: Fig 54 & Fig 55 Images
    place_image_in_cell(tbl2.cell(0, 0), GEOTAG_CONFIGS[4]["img_path"], width_in=2.45)
    place_image_in_cell(tbl2.cell(0, 2), GEOTAG_CONFIGS[5]["img_path"], width_in=2.45)

    # Row 1: Fig 54 & Fig 55 Captions
    format_caption(tbl2.cell(1, 0), 54, GEOTAG_CONFIGS[4]["caption"])
    format_caption(tbl2.cell(1, 2), 55, GEOTAG_CONFIGS[5]["caption"])

    # Insert into DOM
    curr = p_break_before_app
    for elem in [h_app._element, p_intro._element, tbl1._element, p_page_break._element, tbl2._element]:
        curr.addnext(elem)
        curr = elem

    print("Appendix A rebuilt cleanly.")
    print(f"Saving updated report to {DOCX_PATH}...")
    doc.save(DOCX_PATH)
    print("Report saved successfully!")

if __name__ == "__main__":
    main()
