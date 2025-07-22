from flask import Blueprint, request, jsonify
from utils.analyze_gioia import analyze_gioia
import os
import uuid

gioia_bp = Blueprint('gioia', __name__)

@gioia_bp.route('/analyze-gioia', methods=['POST'])
def analyze_gioia_route():
    data = request.get_json()
    interview_data = data.get('interview')
    if not interview_data:
        return jsonify({'error': 'Missing interview data'}), 400
    output_id = str(uuid.uuid4())
    output_path = os.path.join('outputs', f'gioia_{output_id}.md')
    analysis, saved_path = analyze_gioia(interview_data, output_path)
    return jsonify({'analysis': analysis, 'output_path': saved_path}) 