import logging
from typing import Dict

import PyPDF2
import fitz  # PyMuPDF
import openai
import pdfplumber

from utils.docx_parser import extract_text_from_docx


logger = logging.getLogger(__name__)

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
        logger.exception("Error extracting text from persona PDF")
        return ""
    
    return text_content.strip()

def extract_persona_info_with_ai(text_content: str, persona_counter: int) -> Dict:
    """
    Use OpenAI to extract persona information from text content.
    """
    if not text_content.strip():
        return create_default_persona(persona_counter)
    
    try:
        from config import get_secret
        client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
        
        prompt = f"""
        Please analyze the following text and extract persona information for creating an interview character.
        Extract the following information if available:
        
        1. Name (if not available, leave empty)
        2. Age (ONLY if explicitly stated in the text, otherwise leave as null)
        3. Job/Profession
        4. Education level
        5. Personality traits
        6. Opinion on AI/Technology
        7. Opinion on Remote Work
        
        Format your response as JSON with these exact keys:
        {{
            "name": "extracted name or empty string",
            "age": null or number if explicitly stated,
            "job": "job/profession",
            "education": "education level",
            "personality": "personality traits description",
            "ai_opinion": "opinion on AI/technology",
            "remote_work_opinion": "opinion on remote work"
        }}
        
        Do NOT estimate or make up ages. Only include age if it is explicitly stated in the text.
        For other fields, if information is not available, use "Not specified".
        
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
        
        # Ensure all required fields exist (except age, which can be null)
        required_fields = ["name", "job", "education", "personality", "ai_opinion", "remote_work_opinion"]
        for field in required_fields:
            if field not in persona_data or not persona_data[field]:
                persona_data[field] = "Not specified"
        
        # Handle age - only convert if it's a valid number, otherwise leave as null
        age = persona_data.get("age")
        if age is not None and age != "null" and str(age).strip() != "":
            try:
                age = int(age)
            except (ValueError, TypeError):
                age = None
        else:
            age = None
        
        # Convert to the format expected by the app, including original text
        formatted_persona = {
            "name": persona_data["name"],
            "age": age,  # Can be None if not found
            "job": persona_data["job"],
            "education": persona_data["education"],
            "personality": persona_data["personality"],
            "original_text": text_content[:5000],  # Store original text for AI to use
            "opinions": {
                "AI": persona_data["ai_opinion"],
                "Remote Work": persona_data["remote_work_opinion"]
            }
        }
        
        return formatted_persona
        
    except Exception as e:
        logger.exception("Error using AI to extract persona info")
        return create_default_persona(persona_counter)

def create_default_persona(persona_counter: int) -> Dict:
    """
    Create a default persona when extraction fails.
    """
    return {
        "name": f"Persona {persona_counter}",
        "age": None,
        "job": "Professional",
        "education": "College Graduate",
        "personality": "Thoughtful and analytical",
        "original_text": "",
        "opinions": {
            "AI": "Cautiously optimistic about AI technology",
            "Remote Work": "Appreciates flexibility of remote work"
        }
    }

def validate_persona_data(persona_data: Dict) -> Dict:
    """
    Validate and clean persona data.
    """
    # Ensure required fields exist (age can be None)
    required_fields = {
        "name": "Unnamed Persona",
        "job": "Professional",
        "education": "Not specified",
        "personality": "Not specified",
        "opinions": {"AI": "Not specified", "Remote Work": "Not specified"}
    }
    
    for field, default_value in required_fields.items():
        if field not in persona_data or not persona_data[field]:
            persona_data[field] = default_value
    
    # Handle age - only set if it's a valid number, otherwise None
    if "age" not in persona_data or persona_data["age"] is None:
        persona_data["age"] = None
    else:
        try:
            persona_data["age"] = int(persona_data["age"])
        except (ValueError, TypeError):
            persona_data["age"] = None
    
    # Ensure original_text exists
    if "original_text" not in persona_data:
        persona_data["original_text"] = ""
    
    # Ensure opinions is a dict
    if not isinstance(persona_data.get("opinions"), dict):
        persona_data["opinions"] = {"AI": "Not specified", "Remote Work": "Not specified"}
    
    return persona_data
