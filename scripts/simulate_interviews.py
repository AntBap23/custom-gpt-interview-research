import openai
import json
import os

def simulate_interview(persona_path, questions_path, output_path):
    with open(persona_path, 'r') as f:
        persona = json.load(f)

    with open(questions_path, 'r') as f:
        questions = f.readlines()

    intro = f"You are {persona['name']}, a {persona['age']} year old {persona['job']} with traits: {persona['personality']}. Based on this persona, answer the following questions authentically."

    responses = []
    for q in questions:
        prompt = f"{intro}\n\nQuestion: {q.strip()}\nAnswer:"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response['choices'][0]['message']['content']
        responses.append({"question": q.strip(), "answer": answer})

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(responses, f, indent=2)
