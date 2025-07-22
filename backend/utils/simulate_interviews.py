import openai
import json
import os

def simulate_interview(persona, questions, output_path=None):
    """
    Simulate an interview based on persona and questions.
    persona: dict with persona info
    questions: list of strings
    output_path: optional path to save the results as JSON
    Returns: list of {question, answer} dicts, and output_path if saved
    """
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
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(responses, f, indent=2)
    return responses, output_path if output_path else None 