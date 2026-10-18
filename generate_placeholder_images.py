"""
Placeholder Image Generator for UEHIS Service Learning Reports
Generates high-resolution, institutional, publication-quality image placeholders
for Workstation photographs (Figure 32) and Service Learning Logbook pages (Figures 35-49).
"""

import os
from PIL import Image, ImageDraw, ImageFont

def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def get_fonts():
    try:
        font_title = ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf', 44)
        font_h1 = ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf', 36)
        font_h2 = ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf', 28)
        font_body_bold = ImageFont.truetype('C:/Windows/Fonts/timesbd.ttf', 24)
        font_body = ImageFont.truetype('C:/Windows/Fonts/times.ttf', 24)
        font_sm = ImageFont.truetype('C:/Windows/Fonts/times.ttf', 20)
        font_mono = ImageFont.truetype('C:/Windows/Fonts/courbd.ttf', 24)
    except Exception:
        font_title = ImageFont.load_default()
        font_h1 = font_title
        font_h2 = font_title
        font_body_bold = font_title
        font_body = font_title
        font_sm = font_title
        font_mono = font_title
    return {
        'title': font_title,
        'h1': font_h1,
        'h2': font_h2,
        'body_bold': font_body_bold,
        'body': font_body,
        'sm': font_sm,
        'mono': font_mono
    }

def generate_workstation_image(out_path, student_name, role_name, prn_text):
    """
    Generate 960x1280 portrait workstation placeholder image matching Figure 32 dimensions.
    """
    w, h = 960, 1280
    img = Image.new('RGB', (w, h), color='#F1F5F9')
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Outer border
    draw.rectangle([(16, 16), (w - 16, h - 16)], outline='#172B5C', width=5)
    draw.rectangle([(24, 24), (w - 24, h - 24)], outline='#94A3B8', width=2)

    # Top Header Banner (Navy)
    draw.rectangle([(26, 26), (w - 26, 180)], fill='#172B5C')
    draw.text((w // 2, 60), "SYMBIOSIS INSTITUTE OF TECHNOLOGY, PUNE", fill='white', font=fonts['h1'], anchor='mm')
    draw.text((w // 2, 105), "DEPARTMENT OF ARTIFICIAL INTELLIGENCE & MACHINE LEARNING", fill='#E2E8F0', font=fonts['h2'], anchor='mm')
    draw.text((w // 2, 145), "SERVICE LEARNING PROJECT (AY 2026–2027) | CLASS AIML A1 | GROUP 17", fill='#94A3B8', font=fonts['sm'], anchor='mm')

    # Gold Accent Line
    draw.line([(26, 181), (w - 26, 181)], fill='#D97706', width=4)

    # Student & Project Details Card
    card_top = 210
    card_bot = 390
    draw.rectangle([(50, card_top), (w - 50, card_bot)], fill='#FFFFFF', outline='#CBD5E1', width=2)
    
    draw.text((70, card_top + 30), "STUDENT:", fill='#64748B', font=fonts['body_bold'])
    draw.text((220, card_top + 30), student_name, fill='#1E293B', font=fonts['h2'])

    draw.text((70, card_top + 75), "PRN:", fill='#64748B', font=fonts['body_bold'])
    draw.text((220, card_top + 75), prn_text, fill='#1E293B', font=fonts['body_bold'])

    draw.text((70, card_top + 120), "ASSIGNED ROLE:", fill='#64748B', font=fonts['body_bold'])
    draw.text((260, card_top + 120), role_name, fill='#15803D', font=fonts['body_bold'])

    draw.text((70, card_top + 155), "PROJECT:", fill='#64748B', font=fonts['sm'])
    draw.text((220, card_top + 155), "Urban Ecosystem Health Intelligence System (UEHIS)", fill='#1E293B', font=fonts['sm'])

    # Main Photo Placeholder Box
    box_top = 420
    box_bot = 1080
    draw.rectangle([(50, box_top), (w - 50, box_bot)], fill='#F8FAFC', outline='#2563EB', width=3)

    # Dashed inner box effect
    draw.rectangle([(65, box_top + 15), (w - 65, box_bot - 15)], fill='#F8FAFC', outline='#93C5FD', width=2)

    # Camera / Photo Icon / Label
    draw.text((w // 2, box_top + 100), "[ INDIVIDUAL WORKSTATION & FIELDWORK EVIDENCE ]", fill='#1D4ED8', font=fonts['h2'], anchor='mm')
    draw.text((w // 2, box_top + 160), "Figure 32: Authentic Engineering Activity Verification", fill='#1E293B', font=fonts['body_bold'], anchor='mm')

    # Explanatory Guidelines
    guidelines = [
        "This dedicated photographic placeholder verifies the individual contribution of:",
        f"{student_name} ({role_name})",
        "",
        "Verified Engineering Scope Documented:",
        "• Development and execution of assigned technical modules on engineering workstation.",
        "• Collaboration with teammates during hybrid research and code integration sessions.",
        "• Active participation in SEER Bharat Foundation stakeholder reviews and on-field afforestation.",
        "",
        "Instructions for Candidate:",
        "1. Insert high-resolution photograph at engineering workstation or fieldwork location.",
        "2. Ensure image displays active technical tooling, code IDE, GIS interface, or field activity.",
        "3. Verify that institutional setting and timestamp align with documented service hours."
    ]

    y_text = box_top + 220
    for line in guidelines:
        if line.startswith("•") or line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
            draw.text((90, y_text), line, fill='#334155', font=fonts['sm'])
            y_text += 32
        elif line.startswith("Verified") or line.startswith("Instructions"):
            draw.text((90, y_text), line, fill='#0F172A', font=fonts['body_bold'])
            y_text += 35
        elif student_name in line:
            draw.text((w // 2, y_text), line, fill='#15803D', font=fonts['body_bold'], anchor='mm')
            y_text += 40
        else:
            if line:
                draw.text((w // 2, y_text), line, fill='#475569', font=fonts['body'], anchor='mm')
            y_text += 30

    # Stamp Simulation
    draw.rectangle([(w // 2 - 220, box_bot - 140), (w // 2 + 220, box_bot - 40)], outline='#15803D', width=2)
    draw.text((w // 2, box_bot - 105), "SEER BHARAT FOUNDATION, PUNE", fill='#15803D', font=fonts['body_bold'], anchor='mm')
    draw.text((w // 2, box_bot - 65), "DOCUMENTED SERVICE LEARNING RECORD", fill='#15803D', font=fonts['sm'], anchor='mm')

    # Footer
    draw.rectangle([(26, 1110), (w - 26, 1254)], fill='#172B5C')
    draw.text((w // 2, 1145), "Institutional Verification & Academic Compliance Record", fill='#E2E8F0', font=fonts['body_bold'], anchor='mm')
    draw.text((w // 2, 1185), "Mentor: Prof. Darshan Talhande (NGO Mentor of SEER Bharat Foundation)", fill='#94A3B8', font=fonts['sm'], anchor='mm')
    draw.text((w // 2, 1220), "Faculty Coordinator: Dr. Aditi Saxena | Head of Department: Dr. Sumit Kumar", fill='#94A3B8', font=fonts['sm'], anchor='mm')

    img.save(out_path, 'JPEG', quality=95)
    print(f"Generated workstation placeholder: {out_path} ({os.path.getsize(out_path)/1024:.1f} KB)")


def generate_logbook_image(out_path, student_name, role_name, prn_text, week_num, week_date, hours, cum_hours, week_title):
    """
    Generate 1536x2048 portrait logbook placeholder image matching Figures 35-49 dimensions.
    """
    w, h = 1536, 2048
    img = Image.new('RGB', (w, h), color='#F8FAFC')
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Outer double border
    draw.rectangle([(24, 24), (w - 24, h - 24)], outline='#172B5C', width=6)
    draw.rectangle([(36, 36), (w - 36, h - 36)], outline='#94A3B8', width=2)

    # Top Header Banner (Navy)
    draw.rectangle([(38, 38), (w - 38, 240)], fill='#172B5C')
    draw.text((w // 2, 85), "SYMBIOSIS INSTITUTE OF TECHNOLOGY, PUNE", fill='white', font=fonts['title'], anchor='mm')
    draw.text((w // 2, 145), "DEPARTMENT OF ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING", fill='#E2E8F0', font=fonts['h2'], anchor='mm')
    draw.text((w // 2, 195), "SERVICE LEARNING (SL) LOGBOOK — ACADEMIC YEAR 2026–2027", fill='#94A3B8', font=fonts['body_bold'], anchor='mm')

    # Gold Accent Line
    draw.line([(38, 241), (w - 38, 241)], fill='#D97706', width=5)

    # Student & Session Info Grid
    grid_top = 265
    grid_bot = 560
    draw.rectangle([(60, grid_top), (w - 60, grid_bot)], fill='#FFFFFF', outline='#CBD5E1', width=3)
    
    # Internal Dividers
    draw.line([(60, grid_top + 145), (w - 60, grid_top + 145)], fill='#E2E8F0', width=2)
    draw.line([(w // 2, grid_top), (w // 2, grid_top + 145)], fill='#E2E8F0', width=2)

    # Top-Left Box: Student Particulars
    draw.text((80, grid_top + 25), "STUDENT DETAILS", fill='#64748B', font=fonts['sm'])
    draw.text((80, grid_top + 60), f"Name: {student_name}", fill='#0F172A', font=fonts['h2'])
    draw.text((80, grid_top + 105), f"PRN: {prn_text}  |  Class: AIML A1  |  Group: 17", fill='#334155', font=fonts['body'])

    # Top-Right Box: Academic & Partner Details
    draw.text((w // 2 + 30, grid_top + 25), "PROJECT & PARTNER ORGANIZATION", fill='#64748B', font=fonts['sm'])
    draw.text((w // 2 + 30, grid_top + 60), "Project: UEHIS (Urban Ecosystem Health)", fill='#0F172A', font=fonts['body_bold'])
    draw.text((w // 2 + 30, grid_top + 105), "Partner: SEER Bharat Foundation, Pune", fill='#15803D', font=fonts['body_bold'])

    # Bottom Row: Session Particulars
    draw.text((80, grid_top + 165), "LOGBOOK SESSION RECORD", fill='#64748B', font=fonts['sm'])
    draw.text((80, grid_top + 205), f"Week {week_num}: {week_title}", fill='#172B5C', font=fonts['h2'])
    draw.text((80, grid_top + 250), f"Date(s): {week_date}    |    Documented Hours: {hours}    |    Cumulative Progress: {cum_hours}", fill='#1E293B', font=fonts['body_bold'])

    # Main Physical Logbook Scan Placeholder Box
    box_top = 590
    box_bot = 1750
    draw.rectangle([(60, box_top), (w - 60, box_bot)], fill='#F8FAFC', outline='#2563EB', width=4)
    draw.rectangle([(80, box_top + 20), (w - 80, box_bot - 20)], fill='#FFFFFF', outline='#93C5FD', width=2)

    # Title inside box
    draw.text((w // 2, box_top + 80), f"[ VERIFIED LOGBOOK SCAN PLACEHOLDER: WEEK {week_num} ]", fill='#1D4ED8', font=fonts['h1'], anchor='mm')
    draw.text((w // 2, box_top + 130), f"Figure {34 + week_num}: Authentic Scanned Handwritten Record for Week {week_num}", fill='#1E293B', font=fonts['h2'], anchor='mm')
    draw.line([(w // 2 - 350, box_top + 160), (w // 2 + 350, box_top + 160)], fill='#CBD5E1', width=2)

    # Body explanation
    scan_notes = [
        f"This page represents the official verified handwritten logbook entry for Week {week_num} of the Service Learning curriculum.",
        "",
        "Documented Operational Session Highlights:",
        f"• Academic Timeline: {week_date} ({hours})",
        f"• Cumulative Progression: {cum_hours} out of 120 Total Documented Hours",
        f"• Core Assigned Responsibilities: {role_name}",
        f"• Technical Activity: {week_title}",
        "",
        "Institutional Verification Checklist (To Be Attached by Student):",
        "1. Signed physical logbook entry with dated mentor signature from SEER Bharat Foundation.",
        "2. Detailed daily tasks, technical hurdles encountered, and problem-solving logs.",
        "3. Attendance countersigned by Faculty Coordinator Dr. Aditi Saxena (AIML Department, SIT Pune).",
        "4. Institutional rubber stamp and endorsement of SEER Bharat Foundation.",
        "",
        "Instructions for Final Submission:",
        f"• Replace this high-resolution placeholder with the scanned copy of your verified handwritten logbook page.",
        "• Ensure that handwriting, signatures, dates, and organizational stamps are clearly legible."
    ]

    y_scan = box_top + 200
    for line in scan_notes:
        if line.startswith("•") or line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4."):
            draw.text((120, y_scan), line, fill='#334155', font=fonts['body'])
            y_scan += 42
        elif line.startswith("Documented") or line.startswith("Institutional") or line.startswith("Instructions"):
            draw.text((120, y_scan), line, fill='#0F172A', font=fonts['h2'])
            y_scan += 48
        else:
            if line:
                draw.text((w // 2, y_scan), line, fill='#475569', font=fonts['body_bold'], anchor='mm')
            y_scan += 40

    # Institutional Verification Stamp Box
    stamp_top = box_bot - 240
    draw.rectangle([(w // 2 - 320, stamp_top), (w // 2 + 320, stamp_top + 180)], outline='#15803D', width=3)
    draw.text((w // 2, stamp_top + 40), "SEER BHARAT FOUNDATION, PUNE", fill='#15803D', font=fonts['h2'], anchor='mm')
    draw.text((w // 2, stamp_top + 85), "SERVICE LEARNING ATTENDANCE VERIFIED", fill='#15803D', font=fonts['body_bold'], anchor='mm')
    draw.text((w // 2, stamp_top + 130), f"Week {week_num} Record  |  120 Hours Total Engagement", fill='#15803D', font=fonts['sm'], anchor='mm')

    # Footer Signatures Area
    draw.rectangle([(60, 1775), (w - 60, 1990)], fill='#F1F5F9', outline='#CBD5E1', width=2)
    
    # 3 Signatures blocks
    sig_y = 1860
    # Left: Student
    draw.line([(100, sig_y), (420, sig_y)], fill='#64748B', width=2)
    draw.text((260, sig_y + 25), "Student Signature", fill='#1E293B', font=fonts['body_bold'], anchor='mm')
    draw.text((260, sig_y + 55), student_name, fill='#64748B', font=fonts['sm'], anchor='mm')

    # Center: Mentor
    draw.line([(w // 2 - 160, sig_y), (w // 2 + 160, sig_y)], fill='#64748B', width=2)
    draw.text((w // 2, sig_y + 25), "Prof. Darshan Talhande", fill='#1E293B', font=fonts['body_bold'], anchor='mm')
    draw.text((w // 2, sig_y + 55), "NGO Mentor of SEER Bharat Foundation", fill='#64748B', font=fonts['sm'], anchor='mm')

    # Right: Faculty
    draw.line([(w - 420, sig_y), (w - 100, sig_y)], fill='#64748B', width=2)
    draw.text((w - 260, sig_y + 25), "Dr. Aditi Saxena", fill='#1E293B', font=fonts['body_bold'], anchor='mm')
    draw.text((w - 260, sig_y + 55), "Faculty Coordinator, SIT Pune", fill='#64748B', font=fonts['sm'], anchor='mm')

    img.save(out_path, 'JPEG', quality=95)
    print(f"Generated Week {week_num} logbook: {out_path} ({os.path.getsize(out_path)/1024:.1f} KB)")
