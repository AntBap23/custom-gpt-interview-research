from docx import Document
from fpdf import FPDF
from docx2pdf import convert
import json
import os

def export_interview_to_docx(data, docx_path):
    """
    Generate a Word document from interview data.

    @param data: List of {"question": str, "answer": str}
    @param docx_path: Output path for the .docx file
    """
    doc = Document()
    doc.add_heading("Simulated Interview Transcript", level=1)

    for item in data:
        doc.add_heading(f"Q: {item['question']}", level=2)
        doc.add_paragraph(item['answer'])

    os.makedirs(os.path.dirname(docx_path), exist_ok=True)
    doc.save(docx_path)
    print(f"✅ DOCX saved to {docx_path}")


def export_interview_to_pdf(data, pdf_path):
    """
    Generate a PDF file from interview data (cross-platform).

    @param data: List of {"question": str, "answer": str}
    @param pdf_path: Output path for the .pdf file
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Simulated Interview Transcript", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", size=12)
    for item in data:
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 10, f"Q: {item['question']}")
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 10, f"A: {item['answer']}")
        pdf.ln(4)

    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    pdf.output(pdf_path)
    print(f"✅ PDF saved to {pdf_path}")


def export_both(input_json_path, output_basename="full_interviews"):
    """
    Read interview JSON, then export to both DOCX and PDF.

    @param input_json_path: Path to JSON file with interview content
    @param output_basename: Base filename (without extension)
    """
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    docx_path = f"outputs/{output_basename}.docx"
    pdf_path = f"outputs/{output_basename}.pdf"

    export_interview_to_docx(data, docx_path)
    export_interview_to_pdf(data, pdf_path)

    # Optional: Convert DOCX to PDF (Windows only)
    if os.name == 'nt':
        try:
            convert(docx_path, pdf_path.replace(".pdf", "_windows.pdf"))
            print(f"✅ Windows DOCX-to-PDF also saved to: {pdf_path.replace('.pdf', '_windows.pdf')}")
        except Exception as e:
            print("⚠️ DOCX to PDF (Windows) failed:", e)


# Example usage
if __name__ == "__main__":
    export_both("outputs/alex_responses.json")
