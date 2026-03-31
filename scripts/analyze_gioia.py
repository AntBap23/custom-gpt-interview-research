import openai
import os
import json
from config import get_secret


def analyze_gioia(interview_json_path, output_path, settings=None):
    """
    Analyze interview data using Gioia methodology.
    """
    settings = settings or {}

    # Load interview data
    with open(interview_json_path, 'r') as f:
        interview_data = json.load(f)
    
    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    model = settings.get("model", "gpt-3.5-turbo")
    temperature = settings.get("analysis_temperature", 0.3)
    max_tokens = settings.get("analysis_max_tokens", 2000)
    quote_count = settings.get("quote_count", 3)
    analysis_focus = settings.get("analysis_focus", "").strip()
    coding_depth = settings.get("coding_depth", "Standard")
    
    all_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in interview_data])
    
    prompt = (
        "You're a qualitative research assistant using the Gioia methodology.\n"
        "Analyze the following interview data and identify:\n"
        "1. 3 aggregate dimensions\n"
        "2. 3 themes under each dimension\n"
        "3. 3-5 first-order codes under each theme\n"
        f"4. Include up to {quote_count} representative quotes for each theme where useful\n"
        f"5. Coding depth preference: {coding_depth}\n"
    )
    if analysis_focus:
        prompt += f"6. Additional analysis focus: {analysis_focus}\n\n"
    else:
        prompt += "\n"
    prompt += f"Interview Data:\n{all_text}"
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert qualitative researcher. "
                    "Write with methodological clarity and avoid empty repetition."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    analysis = response.choices[0].message.content
    
    # Save analysis
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(analysis)
    
    return analysis
