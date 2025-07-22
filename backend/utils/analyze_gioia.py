import openai
import os
import json

def analyze_gioia(interview_data, output_path=None):
    """
    interview_data: list of {question, answer} dicts
    output_path: optional path to save the analysis
    Returns: analysis string, and output_path if saved
    """
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
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    analysis = response['choices'][0]['message']['content']
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(analysis)
    return analysis, output_path if output_path else None 