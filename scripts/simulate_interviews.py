import openai
import json
import os
from config import get_secret


def simulate_interview(persona_path, questions_path, output_path):
    """
    Simulate an interview based on persona file and questions file.
    """
    # Load persona
    with open(persona_path, 'r') as f:
        persona = json.load(f)
    
    # Load questions
    with open(questions_path, 'r') as f:
        questions = [line.strip() for line in f.readlines() if line.strip()]
    
    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    
    intro = f"You are {persona['name']}, a {persona['age']} year old {persona['job']} with traits: {persona['personality']}. Based on this persona, answer the following questions authentically."
    
    responses = []
    for q in questions:
        prompt = f"{intro}\n\nQuestion: {q.strip()}\nAnswer:"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        responses.append({"question": q.strip(), "answer": answer})
    
    # Save responses
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(responses, f, indent=2)
    
    return responses
