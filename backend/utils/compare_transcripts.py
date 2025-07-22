import difflib
import os
import json

def compare_interviews(real, simulated, output_path=None):
    """
    real: list of {question, answer}
    simulated: list of {question, answer}
    Returns: dict with similarities, differences, emotional_nuance, and output_path if saved
    """
    similarities = []
    differences = []
    emotional_nuance = []
    for r, s in zip(real, simulated):
        if r['question'] == s['question']:
            if r['answer'].strip() == s['answer'].strip():
                similarities.append({'question': r['question'], 'real': r['answer'], 'simulated': s['answer']})
            else:
                diff = list(difflib.unified_diff(r['answer'].splitlines(), s['answer'].splitlines(), lineterm=''))
                differences.append({'question': r['question'], 'real': r['answer'], 'simulated': s['answer'], 'diff': diff})
                # Simple emotional nuance heuristic
                if any(word in r['answer'].lower() for word in ['feel', 'emotion', 'believe', 'think']):
                    emotional_nuance.append({'question': r['question'], 'real': r['answer'], 'simulated': s['answer']})
    result = {
        'similarities': similarities,
        'differences': differences,
        'emotional_nuance': emotional_nuance
    }
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write('# Interview Comparison\n')
            f.write('## Similarities\n')
            for item in similarities:
                f.write(f"- Q: {item['question']}\n  - Real: {item['real']}\n  - Simulated: {item['simulated']}\n")
            f.write('## Differences\n')
            for item in differences:
                f.write(f"- Q: {item['question']}\n  - Real: {item['real']}\n  - Simulated: {item['simulated']}\n  - Diff: {item['diff']}\n")
            f.write('## Emotional Nuance/Missed Points\n')
            for item in emotional_nuance:
                f.write(f"- Q: {item['question']}\n  - Real: {item['real']}\n  - Simulated: {item['simulated']}\n")
        result['output_path'] = output_path
    return result 