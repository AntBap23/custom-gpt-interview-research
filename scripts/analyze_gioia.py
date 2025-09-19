import openai
import os
import json
from config import get_secret


def analyze_gioia(interview_json_path, output_path):
    """
    Analyze interview data using Gioia methodology.
    """
    # Load interview data
    with open(interview_json_path, 'r') as f:
        interview_data = json.load(f)
    
    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    
    all_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in interview_data])
    
    prompt = (
        "You're a qualitative research assistant using the Gioia methodology.\n"
        "Analyze the following interview data and identify:\n"
        "1. 3 aggregate dimensions\n"
        "2. 3 themes under each dimension\n"
        "3. 3-5 first-order codes under each theme\n"
        "4. Include a representative quote for each code\n\n"
        f"Interview Data:\n{all_text}"
    )
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.3
    )
    
    analysis = response.choices[0].message.content
    
    # Save analysis
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(analysis)
    
    return analysis
