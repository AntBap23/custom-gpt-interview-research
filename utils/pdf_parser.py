import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
import openai
import os
from typing import List, Tuple
import re
import streamlit as st

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract text from PDF using multiple methods for best results.
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

def extract_questions_with_ai(text_content: str) -> List[str]:
    """
    Use OpenAI to identify and extract interview questions from text content.
    """
    if not text_content.strip():
        return []
    
    try:
        from config import get_secret
        client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
        
        prompt = f"""
        Please analyze the following text and extract all interview questions. 
        Look for:
        1. Direct questions (ending with ?)
        2. Prompts that ask for responses (e.g., "Tell me about...", "Describe...", "Explain...")
        3. Interview-style statements that expect responses
        
        Format each question on a new line, numbered sequentially.
        Only return the questions, nothing else.
        
        Text to analyze:
        {text_content[:4000]}  # Limit to avoid token limits
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at identifying interview questions from text. Extract only clear, well-formed questions that would be suitable for interviews."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        questions_text = response.choices[0].message.content.strip()
        
        # Parse the numbered questions
        questions = []
        for line in questions_text.split('\n'):
            line = line.strip()
            if line:
                # Remove numbering (1., 2., etc.) and clean up
                cleaned_question = re.sub(r'^\d+\.\s*', '', line).strip()
                if cleaned_question and len(cleaned_question) > 10:  # Filter out very short lines
                    questions.append(cleaned_question)
        
        return questions
        
    except Exception as e:
        st.error(f"Error using AI to extract questions: {str(e)}")
        return []

def validate_and_improve_questions(questions: List[str]) -> List[str]:
    """
    Use AI to validate and improve the extracted questions.
    """
    if not questions:
        return []
    
    try:
        from config import get_secret
        client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
        
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        
        prompt = f"""
        Please review and improve these interview questions. For each question:
        1. Ensure it's clear and well-formed
        2. Make it more engaging if needed
        3. Fix any grammatical issues
        4. Ensure it's suitable for a research interview
        
        Return only the improved questions, one per line, numbered.
        
        Questions to review:
        {questions_text}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at crafting effective interview questions for research purposes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.2
        )
        
        improved_text = response.choices[0].message.content.strip()
        
        # Parse the improved questions
        improved_questions = []
        for line in improved_text.split('\n'):
            line = line.strip()
            if line:
                cleaned_question = re.sub(r'^\d+\.\s*', '', line).strip()
                if cleaned_question and len(cleaned_question) > 10:
                    improved_questions.append(cleaned_question)
        
        return improved_questions
        
    except Exception as e:
        st.error(f"Error improving questions with AI: {str(e)}")
        return questions  # Return original questions if improvement fails

def extract_questions_from_text(text_content: str) -> List[str]:
    """
    Simple regex-based question extraction as fallback.
    """
    questions = []
    
    # Split text into sentences
    sentences = re.split(r'[.!?]+', text_content)
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Look for question patterns
        if (sentence.endswith('?') or 
            sentence.lower().startswith(('what', 'how', 'why', 'when', 'where', 'who', 'which')) or
            sentence.lower().startswith(('tell me', 'describe', 'explain', 'discuss')) or
            'interview question' in sentence.lower()):
            
            if len(sentence) > 15:  # Filter out very short questions
                questions.append(sentence)
    
    return questions
