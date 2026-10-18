"""
Script to update all UEHIS reports (all 4 files):
Replace all mentions of Prof. Darshan Talhande as 'Director' of SEER Bharat
with 'NGO Mentor of SEER Bharat' / 'NGO Mentor Prof. Darshan Talhande' / 'Project Mentor & NGO Mentor'.
"""

import docx
import re
import os
import shutil

BASE_DOCX = "UEHIS_Service_Learning_Report_Aditya_Godar.docx"

def update_aditya_godar_report():
    print("=" * 70)
    print("Step 1: Updating UEHIS_Service_Learning_Report_Aditya_Godar.docx...")
    doc = docx.Document(BASE_DOCX)
    
    # 1. P6: Cover page guidance runs
    p6 = doc.paragraphs[6]
    for r in p6.runs:
        if "Director, SEER Bharat Foundation" in r.text:
            r.text = r.text.replace("Director, SEER Bharat Foundation", "NGO Mentor of SEER Bharat Foundation")
            print("  Cover Page (P6): Updated to 'NGO Mentor of SEER Bharat Foundation'")
            
    # 2. P31: Acknowledgement
    p31 = doc.paragraphs[31]
    for r in p31.runs:
        if "Director of SEER Bharat Foundation" in r.text:
            r.text = r.text.replace("Director of SEER Bharat Foundation", "NGO Mentor of SEER Bharat Foundation")
            print("  Acknowledgement (P31): Updated to 'NGO Mentor of SEER Bharat Foundation'")
            
    # 3. P166: List of Figures Figure 55 Entry
    # Find paragraph with Figure 55 in LOF
    for p in doc.paragraphs[100:180]:
        if "Figure 55." in p.text and "Director Prof. Darshan Talhande" in p.text:
            for r in p.runs:
                if "Director Prof. Darshan Talhande" in r.text:
                    r.text = r.text.replace("Director Prof. Darshan Talhande", "NGO Mentor of SEER Bharat Prof. Darshan Talhande")
                    print(f"  LOF Figure 55: Updated to 'NGO Mentor of SEER Bharat Prof. Darshan Talhande'")

    # 4. P190: Section 1.2 Partner overview
    for p in doc.paragraphs[180:210]:
        if "SEER Bharat Foundation is directed under the leadership of Prof. Darshan Talhande" in p.text:
            for r in p.runs:
                if "is directed under the leadership of Prof. Darshan Talhande" in r.text:
                    r.text = r.text.replace(
                        "is directed under the leadership of Prof. Darshan Talhande",
                        "is guided under the leadership of NGO Mentor Prof. Darshan Talhande"
                    )
                    print("  Section 1.2: Updated to 'guided under the leadership of NGO Mentor Prof. Darshan Talhande'")

    # 5. Table 1, Row 13: Administrative details
    t1 = doc.tables[1]
    if "Project Mentor & NGO Director" in t1.rows[13].cells[0].text:
        t1.rows[13].cells[0].text = "Project Mentor & NGO Mentor"
        print("  Table 1 Row 13: Updated to 'Project Mentor & NGO Mentor'")

    # 6. Table 5, Row 3, Cell 2 (Figure 34 Caption)
    t5 = doc.tables[5]
    cell34 = t5.rows[3].cells[2]
    for p in cell34.paragraphs:
        for r in p.runs:
            if "Director Prof. Darshan Talhande" in r.text:
                r.text = r.text.replace("Director Prof. Darshan Talhande", "NGO Mentor Prof. Darshan Talhande")
                print("  Table 5 Figure 34 Caption: Updated to 'NGO Mentor Prof. Darshan Talhande'")
            elif "Director " in r.text:
                r.text = r.text.replace("Director ", "NGO Mentor ")
                print("  Table 5 Figure 34 Caption (r): Updated to 'NGO Mentor '")

    # 7. Table 28, Row 1, Cell 2 (Figure 55 Caption in Appendix A)
    t28 = doc.tables[28]
    cell55 = t28.rows[1].cells[2]
    for p in cell55.paragraphs:
        for r in p.runs:
            if "Director Prof. Darshan Talhande" in r.text:
                r.text = r.text.replace("Director Prof. Darshan Talhande", "NGO Mentor Prof. Darshan Talhande")
                print("  Table 28 Figure 55 Caption: Updated to 'NGO Mentor Prof. Darshan Talhande'")

    doc.save(BASE_DOCX)
    print(f"Successfully saved updated: {BASE_DOCX} ({os.path.getsize(BASE_DOCX)/(1024*1024):.2f} MB)")

def update_teammate_generator_script():
    print("\n" + "=" * 70)
    print("Step 2: Updating generate_teammate_reports.py...")
    with open("generate_teammate_reports.py", "r", encoding="utf-8") as f:
        code = f.read()

    # Apply text replacements for Director -> NGO Mentor
    code = code.replace("Director Prof. Darshan Talhande", "NGO Mentor Prof. Darshan Talhande")
    code = code.replace("The director commended", "The NGO mentor commended")
    code = code.replace("(Director, SEER Bharat Foundation, Pune)", "(NGO Mentor of SEER Bharat Foundation, Pune)")
    code = code.replace("Director of SEER Bharat Foundation", "NGO Mentor of SEER Bharat Foundation")
    code = code.replace("Director, SEER Bharat Foundation", "NGO Mentor of SEER Bharat Foundation")

    # Update paragraph run clearing to prevent leftover residual runs
    # 1. Weekly narrative and summary
    old_weekly_loop = """        # Heading
        p_head = doc.paragraphs[base_p]
        p_head.runs[0].text = f"7.{w_info['week']} Week {w_info['week']}: {w_info['title']}"

        # Summary line
        p_sum = doc.paragraphs[base_p + 1]
        p_sum.runs[0].text = w_info["summary"]

        # Narrative
        p_narr = doc.paragraphs[base_p + 2]
        p_narr.runs[0].text = w_info["narrative"]

        # Reflection
        p_refl = doc.paragraphs[base_p + 3]
        p_refl.runs[0].text = w_info["reflection"]"""

    new_weekly_loop = """        # Heading
        p_head = doc.paragraphs[base_p]
        p_head.runs[0].text = f"7.{w_info['week']} Week {w_info['week']}: {w_info['title']}"
        for r in p_head.runs[1:]:
            r.text = ""

        # Summary line
        p_sum = doc.paragraphs[base_p + 1]
        p_sum.runs[0].text = w_info["summary"]
        for r in p_sum.runs[1:]:
            r.text = ""

        # Narrative
        p_narr = doc.paragraphs[base_p + 2]
        p_narr.runs[0].text = w_info["narrative"]
        for r in p_narr.runs[1:]:
            r.text = ""

        # Reflection
        p_refl = doc.paragraphs[base_p + 3]
        p_refl.runs[0].text = w_info["reflection"]
        for r in p_refl.runs[1:]:
            r.text = "" """

    if old_weekly_loop in code:
        code = code.replace(old_weekly_loop, new_weekly_loop)
        print("  Replaced weekly loop run-clearing logic.")

    # 2. Section 12.12 points
    old_sec12 = """    for pt_idx in range(9):
        p_pt = doc.paragraphs[449 + pt_idx]
        p_pt.runs[0].text = info["sec12_12_points"][pt_idx]"""

    new_sec12 = """    for pt_idx in range(9):
        p_pt = doc.paragraphs[449 + pt_idx]
        p_pt.runs[0].text = info["sec12_12_points"][pt_idx]
        for r in p_pt.runs[1:]:
            r.text = "" """

    if old_sec12 in code:
        code = code.replace(old_sec12, new_sec12)
        print("  Replaced Section 12.12 run-clearing logic.")

    # 3. Section 14
    old_sec14 = """    for l_idx in range(4):
        p_l = doc.paragraphs[471 + l_idx]
        p_l.runs[0].text = info["learning_outcomes"][l_idx]

    p478 = doc.paragraphs[478]
    p478.runs[0].text = info["technical_challenges"]

    p484 = doc.paragraphs[484]
    p484.runs[0].text = info["personal_reflection"]"""

    new_sec14 = """    for l_idx in range(4):
        p_l = doc.paragraphs[471 + l_idx]
        p_l.runs[0].text = info["learning_outcomes"][l_idx]
        for r in p_l.runs[1:]:
            r.text = ""

    p478 = doc.paragraphs[478]
    p478.runs[0].text = info["technical_challenges"]
    for r in p478.runs[1:]:
        r.text = ""

    p484 = doc.paragraphs[484]
    p484.runs[0].text = info["personal_reflection"]
    for r in p484.runs[1:]:
        r.text = "" """

    if old_sec14 in code:
        code = code.replace(old_sec14, new_sec14)
        print("  Replaced Section 14 run-clearing logic.")

    with open("generate_teammate_reports.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("generate_teammate_reports.py updated successfully!")

if __name__ == "__main__":
    update_aditya_godar_report()
    update_teammate_generator_script()
