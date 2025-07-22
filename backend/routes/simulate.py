from flask import Blueprint, request, jsonify
from utils.simulate_interviews import simulate_interview
import os
import uuid

simulate_bp = Blueprint('simulate', __name__)

@simulate_bp.route('/simulate-interview', methods=['POST'])
def simulate_interview_route():
    data = request.get_json()
    persona = data.get('persona')
    questions = data.get('questions')
    if not persona or not questions:
        return jsonify({'error': 'Missing persona or questions'}), 400
    # Save output to outputs/{uuid}.json
    output_id = str(uuid.uuid4())
    output_path = os.path.join('outputs', f'{output_id}.json')
    responses, saved_path = simulate_interview(persona, questions, output_path)
    return jsonify({'responses': responses, 'output_path': saved_path}) 