"""
Preliminary Pages Builder for UEHIS Service Learning Report
Covers Cover Page, Certificate, Acknowledgement, Abstract, Table of Contents,
List of Figures, and List of Tables with accurate synchronized page numbers.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from report_generator_core import (
    COLOR_NAVY, COLOR_GREEN, COLOR_DARK_TEXT, COLOR_MUTED,
    set_cell_margins, set_cell_borders, format_paragraph,
    add_styled_heading, add_body_p
)

def create_document():
    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)
        section.different_first_page_header_footer = True
    return doc

def build_cover_page(doc):
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(0)
    p_inst.paragraph_format.space_after = Pt(2)
    r1 = p_inst.add_run("DEPARTMENT OF ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING\n")
    r1.font.name = 'Times New Roman'
    r1.font.size = Pt(12)
    r1.font.bold = True
    r1.font.color.rgb = COLOR_NAVY
    
    r2 = p_inst.add_run("SYMBIOSIS INSTITUTE OF TECHNOLOGY, PUNE\n")
    r2.font.name = 'Times New Roman'
    r2.font.size = Pt(11.5)
    r2.font.bold = True
    r2.font.color.rgb = COLOR_DARK_TEXT
    
    r3 = p_inst.add_run("Symbiosis International (Deemed University), Lavale, Pune – 412115\n")
    r3.font.name = 'Times New Roman'
    r3.font.size = Pt(9.5)
    r3.font.color.rgb = COLOR_MUTED

    # Logo image if exists
    if os.path.exists("Logo.png"):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(4)
        p_logo.paragraph_format.space_after = Pt(4)
        r_logo = p_logo.add_run()
        try:
            r_logo.add_picture("Logo.png", width=Inches(1.8))
        except Exception:
            pass

    p_rep = doc.add_paragraph()
    p_rep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_rep.paragraph_format.space_before = Pt(6)
    p_rep.paragraph_format.space_after = Pt(4)
    r_sl = p_rep.add_run("SERVICE LEARNING REPORT\n")
    r_sl.font.name = 'Times New Roman'
    r_sl.font.size = Pt(19)
    r_sl.font.bold = True
    r_sl.font.color.rgb = COLOR_NAVY
    
    r_ind = p_rep.add_run("Individual Final Project Report — Academic Year 2026–27\n")
    r_ind.font.name = 'Times New Roman'
    r_ind.font.size = Pt(12.5)
    r_ind.font.color.rgb = COLOR_DARK_TEXT
    
    p_proj = doc.add_paragraph()
    p_proj.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_proj.paragraph_format.space_before = Pt(10)
    p_proj.paragraph_format.space_after = Pt(4)
    r_pt = p_proj.add_run("Urban Ecosystem Health Intelligence System\n(UEHIS)\n")
    r_pt.font.name = 'Times New Roman'
    r_pt.font.size = Pt(15.5)
    r_pt.font.bold = True
    r_pt.font.color.rgb = COLOR_GREEN

    r_sub = p_proj.add_run("Technical Project: Geospatial Decision Support, Deep Learning Land-Cover Segmentation & Ecological Risk Scoring\n")
    r_sub.font.name = 'Times New Roman'
    r_sub.font.size = Pt(10.5)
    r_sub.font.italic = True
    r_sub.font.color.rgb = COLOR_DARK_TEXT

    r_part = p_proj.add_run("In Association with SEER Bharat Foundation, Pune\n")
    r_part.font.name = 'Times New Roman'
    r_part.font.size = Pt(11)
    r_part.font.bold = True
    r_part.font.color.rgb = COLOR_NAVY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(12)
    p_sub.paragraph_format.space_after = Pt(2)
    r_s1 = p_sub.add_run("Submitted by\n")
    r_s1.font.name = 'Times New Roman'
    r_s1.font.size = Pt(10.5)
    r_s1.font.color.rgb = COLOR_MUTED

    r_name = p_sub.add_run("Aditya Godar\n")
    r_name.font.name = 'Times New Roman'
    r_name.font.size = Pt(13.5)
    r_name.font.bold = True
    r_name.font.color.rgb = COLOR_DARK_TEXT

    r_prn = p_sub.add_run("PRN: 24070126014  |  Class: AIML A1  |  Group No. [FILL IN: Group Number]\n")
    r_prn.font.name = 'Times New Roman'
    r_prn.font.size = Pt(10.5)
    r_prn.font.color.rgb = COLOR_DARK_TEXT

    r_prog = p_sub.add_run("B.Tech. in Artificial Intelligence and Machine Learning, Semester V\n")
    r_prog.font.name = 'Times New Roman'
    r_prog.font.size = Pt(10.5)
    r_prog.font.color.rgb = COLOR_DARK_TEXT

    r_role = p_sub.add_run("Individual Project Role: Computer Vision & Modeling\n")
    r_role.font.name = 'Times New Roman'
    r_role.font.size = Pt(10.5)
    r_role.font.bold = True
    r_role.font.color.rgb = COLOR_GREEN

    p_guid = doc.add_paragraph()
    p_guid.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guid.paragraph_format.space_before = Pt(10)
    p_guid.paragraph_format.space_after = Pt(2)
    r_g1 = p_guid.add_run("Under the guidance of\n")
    r_g1.font.name = 'Times New Roman'
    r_g1.font.size = Pt(10.5)
    r_g1.font.color.rgb = COLOR_MUTED

    r_fac = p_guid.add_run("[FILL IN: Faculty Coordinator Name]\n")
    r_fac.font.name = 'Times New Roman'
    r_fac.font.size = Pt(11)
    r_fac.font.bold = True
    r_fac.font.color.rgb = COLOR_DARK_TEXT

    r_fac_t = p_guid.add_run("Faculty Coordinator, Service Learning\n")
    r_fac_t.font.name = 'Times New Roman'
    r_fac_t.font.size = Pt(10)
    r_fac_t.font.color.rgb = COLOR_DARK_TEXT

    r_hod = p_guid.add_run("[FILL IN: Head of Department Name]\n")
    r_hod.font.name = 'Times New Roman'
    r_hod.font.size = Pt(11)
    r_hod.font.bold = True
    r_hod.font.color.rgb = COLOR_DARK_TEXT

    r_hod_t = p_guid.add_run("Head of Department, Department of AIML\n")
    r_hod_t.font.name = 'Times New Roman'
    r_hod_t.font.size = Pt(10)
    r_hod_t.font.color.rgb = COLOR_DARK_TEXT

    r_ngo = p_guid.add_run("Project Mentor: Prof. Dr. Suvarna P. Patil\n")
    r_ngo.font.name = 'Times New Roman'
    r_ngo.font.size = Pt(11)
    r_ngo.font.bold = True
    r_ngo.font.color.rgb = COLOR_NAVY

    r_ngo_t = p_guid.add_run("Director, SEER Bharat Foundation, Pune\n")
    r_ngo_t.font.name = 'Times New Roman'
    r_ngo_t.font.size = Pt(10)
    r_ngo_t.font.color.rgb = COLOR_DARK_TEXT

    p_bot = doc.add_paragraph()
    p_bot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_bot.paragraph_format.space_before = Pt(10)
    p_bot.paragraph_format.space_after = Pt(0)
    r_inst_foot = p_bot.add_run("Symbiosis Institute of Technology, Pune | Academic Year 2026–27")
    r_inst_foot.font.name = 'Times New Roman'
    r_inst_foot.font.size = Pt(10.5)
    r_inst_foot.font.bold = True
    r_inst_foot.font.color.rgb = COLOR_NAVY
    
    doc.add_page_break()

def build_certificate_page(doc):
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(14)
    r = h.add_run("CERTIFICATE OF COMPLETION & APPROVAL")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    add_body_p(doc, 
        "This is to certify that the Service Learning project report titled \"Urban Ecosystem Health Intelligence System (UEHIS)\" is a bona fide record of work carried out by Aditya Godar (PRN: 24070126014), a student of Semester V, B.Tech. in Artificial Intelligence and Machine Learning, Class AIML A1, at Symbiosis Institute of Technology (SIT), Pune, affiliated with Symbiosis International (Deemed University), during the Academic Year 2026–27.")

    add_body_p(doc, 
        "The project work was conducted in association with SEER Bharat Foundation, Pune (License No. 147561), under the institutional mentorship of Prof. Dr. Suvarna P. Patil (Director, SEER Bharat Foundation) and the academic supervision of the Department of Artificial Intelligence and Machine Learning, Symbiosis Institute of Technology, Pune.")

    add_body_p(doc, 
        "The candidate has successfully completed 120 hours of documented Service Learning work across 15 weeks (5th July 2026 to 16th October 2026), adhering to the prescribed academic regulations, ethical guidelines, and attendance norms of the Institute. The technical documentation, empirical findings, and personal contributions presented in this report represent the student's authentic intellectual effort in Computer Vision & Modeling.")

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(28)
    p_sp.paragraph_format.space_after = Pt(0)

    sig_tbl = doc.add_table(rows=2, cols=2)
    sig_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_tbl.autofit = False
    sig_widths = [Inches(3.2), Inches(3.2)]
    for row in sig_tbl.rows:
        for c_idx, w in enumerate(sig_widths):
            row.cells[c_idx].width = w
            set_cell_borders(row.cells[c_idx], top="none", bottom="none", left="none", right="none")
            set_cell_margins(row.cells[c_idx], top=120, bottom=120, left=60, right=60)

    c00 = sig_tbl.cell(0, 0)
    p00 = c00.paragraphs[0]
    p00.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p00.add_run("_______________________________\nAditya Godar\nStudent (PRN: 24070126014)\nClass: AIML A1\nSymbiosis Institute of Technology, Pune").font.name = 'Times New Roman'
    p00.runs[0].font.size = Pt(10)

    c01 = sig_tbl.cell(0, 1)
    p01 = c01.paragraphs[0]
    p01.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p01.add_run("_______________________________\nProf. Dr. Suvarna P. Patil\nProject Mentor & Director,\nSEER Bharat Foundation, Pune\n[Official Seal & Signature]").font.name = 'Times New Roman'
    p01.runs[0].font.size = Pt(10)

    c10 = sig_tbl.cell(1, 0)
    p10 = c10.paragraphs[0]
    p10.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p10.paragraph_format.space_before = Pt(20)
    p10.add_run("_______________________________\n[FILL IN: Faculty Coordinator Name]\nFaculty Coordinator, Service Learning\nDepartment of AIML\nSymbiosis Institute of Technology, Pune").font.name = 'Times New Roman'
    p10.runs[0].font.size = Pt(10)

    c11 = sig_tbl.cell(1, 1)
    p11 = c11.paragraphs[0]
    p11.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p11.paragraph_format.space_before = Pt(20)
    p11.add_run("_______________________________\n[FILL IN: Head of Department Name]\nHead of Department, AIML\nDepartment of AIML\nSymbiosis Institute of Technology, Pune").font.name = 'Times New Roman'
    p11.runs[0].font.size = Pt(10)

    doc.add_page_break()

def build_acknowledgement_page(doc):
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(12)
    r = h.add_run("Acknowledgement")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    add_body_p(doc, 
        "I express my profound gratitude to the Department of Artificial Intelligence and Machine Learning, Symbiosis Institute of Technology (SIT), Pune, and Symbiosis International (Deemed University), for providing the academic ecosystem and support necessary to undertake this Service Learning project.")

    add_body_p(doc, 
        "I am deeply indebted to our Project Mentor, Prof. Dr. Suvarna P. Patil, Director of SEER Bharat Foundation, Pune, for her invaluable mentorship, scientific direction, and domain guidance throughout the duration of this project. Her deep understanding of urban ecological systems, environmental forestry, and community-driven climate resilience proved instrumental in shaping the objectives and real-world relevance of the Urban Ecosystem Health Intelligence System (UEHIS). We are also grateful to the entire team and field staff at SEER Bharat Foundation for their continuous cooperation during stakeholder reviews and on-field afforestation activities.")

    add_body_p(doc, 
        "I extend my sincere thanks to our Faculty Coordinator, [FILL IN: Faculty Coordinator Name], for continuous institutional supervision, procedural guidance, and constructive feedback throughout the Service Learning curriculum. I also thank [FILL IN: Head of Department Name], Head of Department, AIML, for his encouragement and departmental leadership.")

    add_body_p(doc, 
        "I would like to acknowledge my dedicated project teammates — Aditya Singh Sengar, Abhay Chaturvedi, and Abhay Raj Mosaita. Their exceptional collaboration across data engineering, formula formulation, and full-stack GIS deployment made the development of this complex multi-disciplinary system a truly rewarding team endeavor.")

    p_sign = doc.add_paragraph()
    p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sign.paragraph_format.space_before = Pt(18)
    p_sign.paragraph_format.space_after = Pt(0)
    r_sig = p_sign.add_run("Aditya Godar\nPRN: 24070126014\nB.Tech. AIML (Class A1), Semester V\nSymbiosis Institute of Technology, Pune")
    r_sig.font.name = 'Times New Roman'
    r_sig.font.size = Pt(11)
    r_sig.font.bold = True
    r_sig.font.color.rgb = COLOR_DARK_TEXT

    doc.add_page_break()

def build_abstract_page(doc):
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(12)
    r = h.add_run("Executive Summary / Abstract")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    add_body_p(doc, 
        "Rapid, uncontrolled urbanization across Indian metropolitan centers has precipitated severe environmental distress, marked by the acute intensification of Urban Heat Islands (UHIs), extensive depletion of vegetative tree canopy, and escalating human exposure to micro-climatic hazards. In Pune, municipal authorities and non-governmental environmental organizations such as SEER Bharat Foundation face a persistent operational challenge: urban greening and afforestation initiatives are frequently executed in an ad-hoc or subjective manner due to the absence of a standardized, block-level, multi-sensor spatial decision-support platform.")

    add_body_p(doc, 
        "To resolve this systemic deficiency, our team developed the Urban Ecosystem Health Intelligence System (UEHIS) — an end-to-end geospatial artificial intelligence platform designed to ingest multi-spectral satellite imagery, derive physical land-cover classifications, quantify urban thermal and environmental indicators, and compute an objective, entropy-weighted Urban Ecosystem Health Index (UEHI) at a high spatial resolution of 250 m × 250 m grid blocks. Developed in close partnership with SEER Bharat Foundation, the system transitions environmental decision-making from coarse city-wide generalizations to granular, block-by-block intervention priorities.")

    add_body_p(doc, 
        "As the team member responsible for Computer Vision & Modeling, my core individual contributions centered on architecting the satellite imagery preprocessing pipeline, evaluating land-cover classification workflows, and resolving foundational deep learning validation challenges. Starting from an interim Normalized Difference Vegetation Index (NDVI) thresholding baseline (Canopy > 0.35, Impervious < 0.10), I spearheaded the exploration of deep learning semantic segmentation architectures. During initial experiments with a 4-channel U-Net, I uncovered a critical scientific vulnerability: naive multi-spectral patch extraction with a 128-pixel stride resulted in an approximate 75% spatial overlap between adjacent tiles, causing severe data leakage and artificially inflated accuracy metrics. To ensure scientific rigor and generalization, I engineered a strict geographic buffer train-validation-test split (322 training, 49 validation, and 209 test patches), incorporated Shuttle Radar Topography Mission (SRTM) slope gradients as a 5th input channel to disambiguate rugged topography from built structures, implemented class-weighted loss functions to combat class imbalance, and constructed a 3-model soft-voting ensemble augmented with 8-way test-time augmentation (TTA). On held-out geographic test patches, the model achieved Intersection over Union (IoU) scores of 94.6% for impervious surfaces, 67.9% for tree canopy, 73.5% for water bodies, and 61.2% for pervious ground, with an external benchmark agreement of 97% against Google Dynamic World.")

    add_body_p(doc, 
        "The system pipeline was rigorously validated across the Kothrud pilot study area in Pune, scoring 256 valid blocks with a score distribution spanning 7.4 to 86.4 (mean 42.1) and exhibiting a strong 0.59 correlation with canopy density. The platform incorporates biomass and carbon stock estimation using the ETH Global Canopy Height model and McPherson urban allometry, while establishing defensible criteria for planting-opportunity modeling. Alongside 120 hours of documented service learning across 15 weeks, field tree plantation activities, and mentor reviews, this report provides a thorough, transparent, and reproducible accounting of both the civic engagement and technical computer vision modeling underpinning UEHIS.")

    p_kw = doc.add_paragraph()
    p_kw.paragraph_format.space_before = Pt(8)
    p_kw.paragraph_format.space_after = Pt(0)
    r_kw = p_kw.add_run("Keywords: ")
    r_kw.font.name = 'Times New Roman'
    r_kw.font.bold = True
    r_kw.font.size = Pt(10.5)
    r_kw.font.color.rgb = COLOR_NAVY
    r_kwt = p_kw.add_run("Urban Ecosystem Health, Geospatial Intelligence, Remote Sensing, U-Net Semantic Segmentation, Spatial Data Leakage, Shannon Entropy Weighting, Urban Heat Island, Service Learning.")
    r_kwt.font.name = 'Times New Roman'
    r_kwt.font.italic = True
    r_kwt.font.size = Pt(10.5)
    r_kwt.font.color.rgb = COLOR_DARK_TEXT

    doc.add_page_break()

def build_table_of_contents(doc):
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(12)
    r = h.add_run("Table of Contents")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    toc_items = [
        ("Certificate of Completion & Approval", "ii"),
        ("Acknowledgement", "iii"),
        ("Executive Summary / Abstract", "iv"),
        ("List of Figures", "viii"),
        ("List of Tables", "x"),
        ("PART A: SERVICE LEARNING PROJECT REPORT", "11"),
        ("1. About the Project Partner: SEER Bharat Foundation", "11"),
        ("    1.1 Organizational Profile, Vision, and Mission", "11"),
        ("    1.2 Leadership & Core Environmental Objectives", "11"),
        ("    1.3 Key Ecological Programmes & Community Initiatives", "11"),
        ("    1.4 Sustainable Development Goals (SDGs) Alignment", "12"),
        ("2. Introduction", "13"),
        ("    2.1 Urban Ecological Pressures & Need for Spatial Intelligence", "13"),
        ("    2.2 Purpose and Civic Rationale of UEHIS", "13"),
        ("    2.3 Type of Work Done & Project Synopsis", "13"),
        ("3. Problems Faced in Urban Ecological Management", "14"),
        ("4. Problem Statement and Objectives", "14"),
        ("    4.1 Problem Statement", "14"),
        ("    4.2 Objectives of the Work", "15"),
        ("5. Project Administrative Details", "15"),
        ("6. Methodological Framework", "16"),
        ("7. Work Done at SEER Bharat Foundation (Weekly Documentation)", "17"),
        ("    7.1 Week 1: Setup, Planning & Architecture Selection", "18"),
        ("    7.2 Week 2: Initial U-Net Implementation & Satellite Pipeline", "18"),
        ("    7.3 Week 3: Multispectral Preprocessing & Feature Extraction", "18"),
        ("    7.4 Week 4: Interim NDVI Thresholding & Baseline Classification", "19"),
        ("    7.5 Week 5: Pipeline Architecture & Preprocessing Synchronization", "19"),
        ("    7.6 Week 6: Post-CA2 Review, Dynamic World Ingestion & 4-Class Scheme", "19"),
        ("    7.7 Week 7: Training Patch Preparation, Remapping & Imbalance Audit", "20"),
        ("    7.8 Week 8: Initial Training, 75% Leakage Discovery & Buffer Split", "20"),
        ("    7.9 Week 9: Geographic Partitioning, SRTM Slope & Mask Curation", "21"),
        ("    7.10 Week 10: Slope-Aware U-Net Training & Hyperparameter Tuning", "21"),
        ("    7.11 Week 11: 3-Model Soft-Voting Ensemble & Afforestation Drive", "22"),
        ("    7.12 Week 12: Production Sliding-Window Inference & DW Benchmark", "22"),
        ("    7.13 Week 13: System Integration, PostGIS & Web Dashboard Coupling", "23"),
        ("    7.14 Week 14: Municipal Stakeholder Evaluation & Kothrud Testing", "23"),
        ("    7.15 Week 15: Final Engineering Audit, Handover & Mentor Sign-Off", "23"),
        ("8. Day-wise and Week-wise Service Learning Hours Summary", "24"),
        ("9. Student Time Log & Verification (Annexure-3)", "25"),
        ("10. Photographic Evidence & Geotag Verification", "25"),
        ("11. Logbook Scanned Documentation", "26"),
        ("PART B: TECHNICAL PROJECT DOCUMENTATION — UEHIS", "34"),
        ("12. Technical Project: Urban Ecosystem Health Intelligence System", "34"),
        ("    12.1 Project Overview & Repository Infrastructure", "34"),
        ("    12.2 UEHIS Core Team Structure & Task Allocation", "34"),
        ("    12.3 Complete Technology Stack & Multi-Sensor Geospatial Datasets", "35"),
        ("    12.4 Functional & Non-Functional System Requirements", "37"),
        ("    12.5 System Architecture & Modular 5-Phase Pipeline", "38"),
        ("    12.6 Phase 1: Satellite Data Ingestion & Geospatial Preprocessing", "38"),
        ("    12.7 Phase 2: Computer Vision, Land-Cover Modeling & Experiments", "39"),
        ("    12.8 Phase 3: Urban Ecosystem Health Index (UEHI) Scoring Engine", "44"),
        ("    12.9 Phase 4: Environmental Interventions — Carbon & Planting Audit", "48"),
        ("    12.10 Phase 5: Interactive Web Dashboard & Spatial UI Integration", "49"),
        ("    12.11 System Verification, Engineering Audits & Regression Testing", "50"),
        ("    12.12 Individual Role & Detailed Contribution: Aditya Godar (Computer Vision)", "50"),
        ("    12.13 Known Limitations, Technical Gaps & Future Roadmaps", "51"),
        ("13. Summary of Work (Comparative Analysis)", "52"),
        ("14. Conclusion & Learning Outcomes", "52"),
        ("    14.1 Technical Learning Outcomes", "52"),
        ("    14.2 Socio-Ecological & Community Implications", "53"),
        ("    14.3 Obstacles & Overcoming Technical Challenges", "53"),
        ("    14.4 Strategic Recommendations for SEER Bharat Foundation", "53"),
        ("    14.5 Personal Reflection", "53"),
        ("15. References & Academic Bibliography", "54"),
        ("Appendix A: SEER Bharat Foundation Progress Confirmation Letter", "55")
    ]

    for item, page in toc_items:
        p_t = doc.add_paragraph()
        format_paragraph(p_t, space_before=1, space_after=2, line_spacing=1.05, align=WD_ALIGN_PARAGRAPH.LEFT)
        if item.startswith("PART"):
            r_item = p_t.add_run(item)
            r_item.font.bold = True
            r_item.font.size = Pt(10)
            r_item.font.color.rgb = COLOR_NAVY
        elif item.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "11.", "12.", "13.", "14.", "15.", "Appendix")):
            r_item = p_t.add_run(item)
            r_item.font.bold = True
            r_item.font.size = Pt(9.5)
            r_item.font.color.rgb = COLOR_DARK_TEXT
        else:
            r_item = p_t.add_run(item)
            r_item.font.size = Pt(9)
            r_item.font.color.rgb = COLOR_DARK_TEXT
        
        leader_len = max(2, 85 - len(item))
        r_dots = p_t.add_run(" " + "." * leader_len + " ")
        r_dots.font.size = Pt(8.5)
        r_dots.font.color.rgb = COLOR_MUTED
        
        r_pg = p_t.add_run(page)
        r_pg.font.bold = True
        r_pg.font.size = Pt(9)
        r_pg.font.color.rgb = COLOR_DARK_TEXT

    doc.add_page_break()

def build_list_of_figures(doc):
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(12)
    r = h.add_run("List of Figures")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    figures_list = [
        (1, "UEHIS High-Level System Architecture and 5-Phase Processing Pipeline", "17"),
        (2, "End-to-End Methodological Workflow from Satellite Ingestion to Spatial Dashboard", "17"),
        (3, "Sentinel-2 Multi-Spectral Surface Reflectance Composite of Pune Metropolitan Area", "39"),
        (4, "Kothrud Pilot Study Area Spatial Extent and Fixed 250m Grid Lattice (EPSG:32643)", "39"),
        (5, "Sentinel-2 Derived Interim NDVI Vegetation Index Heatmap for Kothrud Pilot Ward", "40"),
        (6, "Interim 3-Class Land-Cover Map Derived via NDVI Thresholding", "40"),
        (7, "OpenStreetMap (OSM) Extraction: 12,758 Building Polygons & 4,705 Road Segments", "39"),
        (8, "Four-Class Land-Cover Remapping Scheme from Google Dynamic World", "42"),
        (9, "Demonstration of 75% Patch Overlap Data Leakage vs. Buffer-Separated Partitioning", "42"),
        (10, "Geographic Train-Validation-Test Partitioning Layout Across Pune (322/49/209 Patches)", "42"),
        (11, "5-Channel U-Net Deep Learning Semantic Segmentation Architecture with SRTM Slope", "40"),
        (12, "U-Net Training and Validation Loss Curves Across 50 Epochs with Class-Weighted Loss", "42"),
        (13, "8-Way Test-Time Augmentation (TTA) Transformation Scheme for Inference Robustness", "42"),
        (14, "Overlapping Sliding-Window Inference with 2D Bartlett Window Blending", "42"),
        (15, "Confusion Matrix and Class-Wise IoU Performance on Held-Out Geographic Test Set", "44"),
        (16, "U-Net Model Inference Segmentation vs. Google Dynamic World External Benchmark", "44"),
        (17, "Shannon Entropy Weight Derivation and 6-Factor Objective Weight Distribution", "45"),
        (18, "Direction-Aware Min-Max Indicator Normalization Response Curves", "45"),
        (19, "Canopy-Temperature Synergy Function ($S_i$) vs. Population Penalty Multiplier ($m_i$)", "47"),
        (20, "Authoritative UEHI Score Distribution Histogram Across 256 Validated Kothrud Blocks", "47"),
        (21, "Authoritative Block-Level UEHI Score Heatmap for Kothrud Pilot Study Area", "47"),
        (22, "Four-Tier Ecological Risk Classification Choropleth Map (Critical, High, Moderate, Low)", "47"),
        (23, "Block-Level Above-Ground Biomass and Carbon Stock Map Based on ETH Canopy Height", "48"),
        (24, "Discrepancy: Planar UTM Block Carbon vs. Interactive Point-Radius WGS84 Calculation", "48"),
        (25, "Conceptual Block-Level Planting Opportunity Prioritization Map", "49"),
        (26, "UEHIS Web Dashboard Home Interface Featuring Interactive Vector Map and Ward Filtering", "49"),
        (27, "Granular Block Inspection Modal Deconstructing 6-Factor Scores and Risk Tier", "50"),
        (28, "Interactive 1 km Point-Radius Study Area Environmental Analysis Tool", "50"),
        (29, "Automated Software Verification: Complete Pytest Test Suite Report (197 Passing Tests)", "50"),
        (30, "GitHub Commit History and Version Control Progress Logs for the UEHIS Repository", "50"),
        (31, "Group Geotag Verification Photo of UEHIS Team at SEER Bharat Foundation HQ", "26"),
        (32, "Individual Work Geotag Photo: Aditya Godar at Modeling Workstation", "26"),
        (33, "On-Field Afforestation Activity: Tree Plantation Drive with SEER Bharat (18-09-2026)", "26"),
        (34, "Technical Review and Presentation Session with Project Mentor Prof. Dr. Suvarna Patil", "26"),
        (35, "Service Learning Logbook Scanned Page: Week 1 Activities (Setup and Planning)", "27"),
        (36, "Service Learning Logbook Scanned Page: Week 2 Activities (Data Pipeline Development)", "27"),
        (37, "Service Learning Logbook Scanned Page: Week 3 Activities (Multispectral Preprocessing)", "27"),
        (38, "Service Learning Logbook Scanned Page: Week 4 Activities (Interim NDVI Classification)", "27"),
        (39, "Service Learning Logbook Scanned Page: Week 5 Activities (Pipeline Synchronization)", "28"),
        (40, "Service Learning Logbook Scanned Page: Week 6 Activities (Dynamic World Remapping)", "28"),
        (41, "Service Learning Logbook Scanned Page: Week 7 Activities (Training Patch Preparation)", "29"),
        (42, "Service Learning Logbook Scanned Page: Week 8 Activities (Spatial Data Leakage Discovery)", "29"),
        (43, "Service Learning Logbook Scanned Page: Week 9 Activities (Geographic Buffer Partitioning)", "29"),
        (44, "Service Learning Logbook Scanned Page: Week 10 Activities (Slope-Aware Model Training)", "29"),
        (45, "Service Learning Logbook Scanned Page: Week 11 Activities (Ensemble & Afforestation Drive)", "30"),
        (46, "Service Learning Logbook Scanned Page: Week 12 Activities (Sliding-Window Inference)", "30"),
        (47, "Service Learning Logbook Scanned Page: Week 13 Activities (PostGIS Integration)", "31"),
        (48, "Service Learning Logbook Scanned Page: Week 14 Activities (Municipal Testing & Evaluation)", "31"),
        (49, "Service Learning Logbook Scanned Page: Week 15 Activities (Final Audit & Handover)", "32"),
        (50, "Progress Confirmation Letter from SEER Bharat Foundation (20% Milestone, Page 1)", "55"),
        (51, "Progress Confirmation Letter from SEER Bharat Foundation (20% Milestone, Page 2)", "55")
    ]

    for idx, (num, cap, pg) in enumerate(figures_list):
        if idx == 26:
            doc.add_page_break()
            h_cont = doc.add_paragraph()
            h_cont.alignment = WD_ALIGN_PARAGRAPH.LEFT
            h_cont.paragraph_format.space_before = Pt(10)
            h_cont.paragraph_format.space_after = Pt(12)
            r_cont = h_cont.add_run("List of Figures (Continued)")
            r_cont.font.name = 'Times New Roman'
            r_cont.font.size = Pt(14)
            r_cont.font.bold = True
            r_cont.font.color.rgb = COLOR_NAVY

        p_f = doc.add_paragraph()
        format_paragraph(p_f, space_before=1, space_after=3, line_spacing=1.1, align=WD_ALIGN_PARAGRAPH.LEFT)
        r_f = p_f.add_run(f"Figure {num}.  {cap}")
        r_f.font.size = Pt(9)
        r_f.font.color.rgb = COLOR_DARK_TEXT
        
        leader_len = max(2, 80 - len(f"Figure {num}.  {cap}"))
        r_dots = p_f.add_run(" " + "." * leader_len + " ")
        r_dots.font.size = Pt(8.5)
        r_dots.font.color.rgb = COLOR_MUTED
        
        r_pg = p_f.add_run(pg)
        r_pg.font.bold = True
        r_pg.font.size = Pt(9)
        r_pg.font.color.rgb = COLOR_DARK_TEXT

    doc.add_page_break()

def build_list_of_tables(doc):
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(12)
    r = h.add_run("List of Tables")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = COLOR_NAVY

    tables_list = [
        (1, "Sustainable Development Goals (SDGs) Addressed by UEHIS and SEER Bharat Foundation", "12"),
        (2, "Service Learning Administrative & Project Details Specification", "15"),
        (3, "Summary of Documented Service Learning Hours by Week (Aditya Godar, 120 Hours Total)", "24"),
        (4, "UEHIS Core Team Structure, Individual Roles, and Domain Responsibilities", "34"),
        (5, "Comprehensive Technology Stack, Software Libraries, and Functional Roles", "35"),
        (6, "Primary Geospatial Datasets, Satellite Sensors, and Provenance Metadata", "36"),
        (7, "Quantitative Evaluation Metrics (IoU & F1-Score) of U-Net on Geographic Test Set", "43"),
        (8, "Active 6-Factor UEHI Indicator Configuration, Normalization Direction, and Weights", "44"),
        (9, "Ecological Risk Tier Categorization, Score Intervals, and Intervention Mandates", "46"),
        (10, "Comparative Summary of Service Learning (Part A) vs. Technical Engineering (Part B)", "52")
    ]

    for num, cap, pg in tables_list:
        p_t = doc.add_paragraph()
        format_paragraph(p_t, space_before=2, space_after=2, line_spacing=1.05, align=WD_ALIGN_PARAGRAPH.LEFT)
        r_t = p_t.add_run(f"Table {num}.  {cap}")
        r_t.font.size = Pt(9.5)
        r_t.font.color.rgb = COLOR_DARK_TEXT
        
        leader_len = max(2, 80 - len(f"Table {num}.  {cap}"))
        r_dots = p_t.add_run(" " + "." * leader_len + " ")
        r_dots.font.size = Pt(8.5)
        r_dots.font.color.rgb = COLOR_MUTED
        
        r_pg = p_t.add_run(pg)
        r_pg.font.bold = True
        r_pg.font.size = Pt(9)
        r_pg.font.color.rgb = COLOR_DARK_TEXT

    doc.add_page_break()

print("Synchronized preliminary pages builder ready.")
