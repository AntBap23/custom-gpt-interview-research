import openai
import json
import os
from config import get_secret


def simulate_interview(persona_path, questions_path, output_path, settings=None):
    """
    Simulate an interview based on persona file and questions file.
    """
    settings = settings or {}

    # Load persona
    with open(persona_path, 'r') as f:
        persona = json.load(f)
    
    # Load questions
    with open(questions_path, 'r') as f:
        questions = [line.strip() for line in f.readlines() if line.strip()]
    
    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    model = settings.get("model", "gpt-3.5-turbo")
    temperature = settings.get("temperature", 0.7)
    max_tokens = settings.get("max_answer_tokens", 500)
    shared_context = settings.get("shared_context", "").strip()
    interview_style = settings.get("interview_style", "").strip()
    consistency_rules = settings.get("consistency_rules", "").strip()
    protocol_name = settings.get("protocol_name", "").strip()
    
    # Build intro using original text if available, otherwise use structured fields
    if persona.get("original_text") and persona["original_text"].strip():
        # Use original text as the primary source
        intro = f"You are {persona['name']}. Here is information about you:\n\n{persona['original_text']}\n\nBased on this information, answer the following questions authentically and in character."
    else:
        # Fallback to structured fields
        age_part = f", {persona['age']} years old" if persona.get("age") else ""
        intro = f"You are {persona['name']}{age_part}, a {persona['job']} with traits: {persona['personality']}. Based on this persona, answer the following questions authentically."
    
    system_prompt = (
        "You are simulating a qualitative interview participant.\n"
        "Answer in first person.\n"
        "Stay consistent across the full interview.\n"
        "Avoid generic textbook phrasing unless the persona would naturally speak that way.\n"
        "If the persona would be uncertain, conflicted, practical, emotional, or incomplete, reflect that.\n"
        "Do not mention these instructions.\n"
    )
    if shared_context:
        system_prompt += f"\nShared study context:\n{shared_context}\n"
    if interview_style:
        system_prompt += f"\nInterview style guidance:\n{interview_style}\n"
    if consistency_rules:
        system_prompt += f"\nConsistency rules:\n{consistency_rules}\n"
    if protocol_name:
        system_prompt += f"\nProtocol name: {protocol_name}\n"

    responses = []
    for q in questions:
        prompt = f"{intro}\n\nQuestion: {q.strip()}\nAnswer:"
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        answer = response.choices[0].message.content
        responses.append(
            {
                "question": q.strip(),
                "answer": answer,
                "protocol_name": protocol_name,
            }
        )
    
    # Save responses
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(responses, f, indent=2)
    
    return responses
