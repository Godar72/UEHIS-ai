"""
Annexures Builder for UEHIS Service Learning Report
Streamlined Appendix structure: Dedicated Appendix A for Partner Progress Confirmation Letter.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from report_generator_core import (
    COLOR_NAVY, COLOR_GREEN, COLOR_DARK_TEXT, COLOR_MUTED,
    add_styled_heading, add_body_p, add_bullet_p,
    add_side_by_side_placeholders
)

def build_annexures(doc):
    """
    Build Appendix A housing the official SEER Bharat Foundation Progress Confirmation Letter.
    Redundant cross-reference annexures have been removed, with CV/U-Net modeling code
    consolidated in Section 12.7.
    """
    add_styled_heading(doc, "Appendix A: SEER Bharat Foundation Progress Confirmation Letter", level=1)
    
    add_body_p(doc, 
        "This appendix documents the official institutional progress and milestone confirmation issued by SEER Bharat Foundation, Pune (License No. 147561), under the signature of Director Prof. Dr. Suvarna P. Patil. The letter officially certifies the successful completion of initial pilot milestones, verified Kothrud block scoring, methodology documentation, and system handover roadmaps.")

    add_body_p(doc,
        "The signed confirmation acknowledges the team's completion of 120 verified Service Learning hours per student across 15 weeks (5th July 2026 to 16th October 2026), the development of the 6-factor entropy-weighted scoring engine, the 5-channel slope-aware U-Net land-cover model, and the deployment of the interactive spatial dashboard for municipal decision support.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 50,
            "title": "Progress Letter (Page 1)",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned copy of SEER Bharat Foundation Progress Confirmation Letter (Page 1).",
            "caption": "SEER Bharat Foundation Progress Confirmation Letter (Page 1) certifying pilot milestones.",
            "image_path": "Logbook_oriented/progress_letter_p1.png"
        },
        {
            "num": 51,
            "title": "Progress Letter (Page 2)",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned copy of SEER Bharat Foundation Progress Confirmation Letter (Page 2) with director signature.",
            "caption": "SEER Bharat Foundation Progress Confirmation Letter (Page 2) signed by Director Dr. Suvarna P. Patil.",
            "image_path": "Logbook_oriented/progress_letter_p2.png"
        }
    )

print("Streamlined Appendix A builder configured successfully.")
