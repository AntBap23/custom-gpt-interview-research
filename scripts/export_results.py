from docx import Document
from fpdf import FPDF
import json
import os

def export_interview_to_docx(data, docx_path):
    """Export interview data to DOCX format."""
    doc = Document()
    doc.add_heading("Simulated Interview Transcript", level=1)
    
    for item in data:
        doc.add_heading(f"Q: {item['question']}", level=2)
        doc.add_paragraph(item['answer'])
    
    os.makedirs(os.path.dirname(docx_path), exist_ok=True)
    doc.save(docx_path)
    return docx_path

def export_interview_to_pdf(data, pdf_path):
    """Export interview data to PDF format."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Simulated Interview Transcript", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    
    for item in data:
        pdf.set_font("Arial", 'B', 12)
        # Handle encoding issues
        question = item['question'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, f"Q: {question}")
        
        pdf.set_font("Arial", '', 12)
        answer = item['answer'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, f"A: {answer}")
        pdf.ln(4)
    
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    pdf.output(pdf_path)
    return pdf_path

def export_both(input_json_path, output_basename):
    """Export interview data to both DOCX and PDF formats."""
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    output_dir = "outputs"
    docx_path = os.path.join(output_dir, f"{output_basename}.docx")
    pdf_path = os.path.join(output_dir, f"{output_basename}.pdf")
    
    export_interview_to_docx(data, docx_path)
    export_interview_to_pdf(data, pdf_path)
    
    return docx_path, pdf_path
