import os
import sys
import time

def export_to_pdf():
    docx_path = os.path.abspath("UEHIS_Service_Learning_Report_Aditya_Godar.docx")
    pdf_path = os.path.abspath("UEHIS_Service_Learning_Report_Aditya_Godar.pdf")
    
    print(f"Exporting: {docx_path}")
    print(f"Target PDF: {pdf_path}")
    
    import win32com.client
    word = None
    word_doc = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone
        
        print("Opening Word document...")
        word_doc = word.Documents.Open(docx_path, ReadOnly=True)
        
        print("Exporting as PDF (wdExportFormatPDF = 17)...")
        # wdExportFormatPDF = 17, wdExportOptimizeForPrint = 0
        word_doc.ExportAsFixedFormat(
            OutputFileName=pdf_path,
            ExportFormat=17,
            OpenAfterExport=False,
            OptimizeFor=0,
            CreateBookmarks=1,  # wdExportCreateHeadingBookmarks
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False
        )
        print("Export completed successfully!")
        
        pdf_size = os.path.getsize(pdf_path)
        print(f"Exported PDF size: {pdf_size / (1024*1024):.2f} MB ({pdf_size} bytes)")
    except Exception as e:
        print(f"Error during Word COM conversion: {e}")
        raise
    finally:
        if word_doc is not None:
            try:
                word_doc.Close(SaveChanges=False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        print("Word application closed.")

if __name__ == "__main__":
    export_to_pdf()
