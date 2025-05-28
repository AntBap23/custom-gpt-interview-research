import openai
import json
import os

def analyze_gioia(input_path, output_path):
    with open(input_path, 'r') as f:
        data = json.load(f)

    all_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in data])
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

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(analysis)
