import json
import os
from collections import Counter
import pandas as pd

def analyze_responses(responses_dir="data/ai_responses", output_dir="outputs"):
    """
    Analyze all interview responses and generate summary statistics.
    """
    if not os.path.exists(responses_dir):
        print(f"No responses directory found at {responses_dir}")
        return
    
    response_files = [f for f in os.listdir(responses_dir) if f.endswith('.json')]
    
    if not response_files:
        print("No response files found")
        return
    
    all_responses = []
    personas = []
    
    for file in response_files:
        file_path = os.path.join(responses_dir, file)
        with open(file_path, 'r') as f:
            data = json.load(f)
            all_responses.extend(data)
            persona_name = file.replace('_responses.json', '')
            personas.append(persona_name)
    
    # Basic statistics
    total_questions = len(all_responses)
    unique_questions = len(set([r['question'] for r in all_responses]))
    
    print(f"📊 Analysis Summary:")
    print(f"Total responses: {total_questions}")
    print(f"Unique questions: {unique_questions}")
    print(f"Personas analyzed: {len(personas)}")
    
    # Save summary
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, "analysis_summary.txt")
    
    with open(summary_path, 'w') as f:
        f.write(f"Interview Analysis Summary\n")
        f.write(f"========================\n\n")
        f.write(f"Total responses: {total_questions}\n")
        f.write(f"Unique questions: {unique_questions}\n")
        f.write(f"Personas analyzed: {len(personas)}\n\n")
        f.write(f"Personas:\n")
        for persona in personas:
            f.write(f"- {persona}\n")
    
    print(f"✅ Summary saved to {summary_path}")
    return summary_path

if __name__ == "__main__":
    analyze_responses()