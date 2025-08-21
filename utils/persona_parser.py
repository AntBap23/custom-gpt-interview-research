import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
import openai
import os
from typing import Dict, Optional
import re
import streamlit as st
from docx import Document

def extract_text_from_docx(docx_file) -> str:
    """
    Extract text from DOCX file.
    """
    try:
        doc = Document(docx_file)
        text_content = ""
        for paragraph in doc.paragraphs:
            text_content += paragraph.text + "\n"
        return text_content.strip()
    except Exception as e:
        st.error(f"Error extracting text from DOCX: {str(e)}")
        return ""

def extract_text_from_pdf_persona(pdf_file) -> str:
    """
    Extract text from PDF using multiple methods for persona parsing.
    """
    text_content = ""
    
    try:
        # Method 1: Try pdfplumber first (best for structured text)
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
        
        # If pdfplumber didn't extract much text, try PyMuPDF
        if len(text_content.strip()) < 100:
            pdf_file.seek(0)  # Reset file pointer
            pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
            text_content = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text_content += page.get_text() + "\n"
            pdf_document.close()
        
        # If still not much text, try PyPDF2 as fallback
        if len(text_content.strip()) < 100:
            pdf_file.seek(0)  # Reset file pointer
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
                
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""
    
    return text_content.strip()

def extract_persona_info_with_ai(text_content: str, persona_counter: int) -> Dict:
    """
    Use OpenAI to extract persona information from text content.
    """
    if not text_content.strip():
        return create_default_persona(persona_counter)
    
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""
        Please analyze the following text and extract persona information for creating an interview character.
        Extract the following information if available:
        
        1. Name (if not available, leave empty)
        2. Age (estimate if not explicitly stated)
        3. Job/Profession
        4. Education level
        5. Personality traits
        6. Opinion on AI/Technology
        7. Opinion on Remote Work
        
        Format your response as JSON with these exact keys:
        {{
            "name": "extracted name or empty string",
            "age": estimated_age_number,
            "job": "job/profession",
            "education": "education level",
            "personality": "personality traits description",
            "ai_opinion": "opinion on AI/technology",
            "remote_work_opinion": "opinion on remote work"
        }}
        
        If information is not available, make reasonable assumptions based on context.
        
        Text to analyze:
        {text_content[:3000]}  # Limit to avoid token limits
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at extracting persona information from text. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.2
        )
        
        # Parse the JSON response
        import json
        persona_data = json.loads(response.choices[0].message.content.strip())
        
        # Handle missing name
        if not persona_data.get("name") or persona_data["name"].strip() == "":
            persona_data["name"] = f"Persona {persona_counter}"
        
        # Ensure all required fields exist
        required_fields = ["name", "age", "job", "education", "personality", "ai_opinion", "remote_work_opinion"]
        for field in required_fields:
            if field not in persona_data or not persona_data[field]:
                persona_data[field] = "Not specified"
        
        # Convert to the format expected by the app
        formatted_persona = {
            "name": persona_data["name"],
            "age": int(persona_data["age"]) if str(persona_data["age"]).isdigit() else 30,
            "job": persona_data["job"],
            "education": persona_data["education"],
            "personality": persona_data["personality"],
            "opinions": {
                "AI": persona_data["ai_opinion"],
                "Remote Work": persona_data["remote_work_opinion"]
            }
        }
        
        return formatted_persona
        
    except Exception as e:
        st.error(f"Error using AI to extract persona info: {str(e)}")
        return create_default_persona(persona_counter)

def create_default_persona(persona_counter: int) -> Dict:
    """
    Create a default persona when extraction fails.
    """
    return {
        "name": f"Persona {persona_counter}",
        "age": 30,
        "job": "Professional",
        "education": "College Graduate",
        "personality": "Thoughtful and analytical",
        "opinions": {
            "AI": "Cautiously optimistic about AI technology",
            "Remote Work": "Appreciates flexibility of remote work"
        }
    }

def validate_persona_data(persona_data: Dict) -> Dict:
    """
    Validate and clean persona data.
    """
    # Ensure required fields exist
    required_fields = {
        "name": "Unnamed Persona",
        "age": 30,
        "job": "Professional",
        "education": "Not specified",
        "personality": "Not specified",
        "opinions": {"AI": "Not specified", "Remote Work": "Not specified"}
    }
    
    for field, default_value in required_fields.items():
        if field not in persona_data or not persona_data[field]:
            persona_data[field] = default_value
    
    # Ensure age is a number
    try:
        persona_data["age"] = int(persona_data["age"])
    except (ValueError, TypeError):
        persona_data["age"] = 30
    
    # Ensure opinions is a dict
    if not isinstance(persona_data.get("opinions"), dict):
        persona_data["opinions"] = {"AI": "Not specified", "Remote Work": "Not specified"}
    
    return persona_data
