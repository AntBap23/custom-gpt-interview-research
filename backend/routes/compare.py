from flask import Blueprint, request, jsonify
from utils.compare_transcripts import compare_interviews
import os
import uuid

compare_bp = Blueprint('compare', __name__)

@compare_bp.route('/compare-interview', methods=['POST'])
def compare_interview_route():
    data = request.get_json()
    real = data.get('real')
    simulated = data.get('simulated')
    if not real or not simulated:
        return jsonify({'error': 'Missing real or simulated data'}), 400
    output_id = str(uuid.uuid4())
    output_path = os.path.join('outputs', f'compare_{output_id}.md')
    result = compare_interviews(real, simulated, output_path)
    return jsonify(result) 