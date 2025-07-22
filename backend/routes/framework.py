from flask import Blueprint, request, jsonify
from utils.generate_framework import generate_framework
import os
import uuid

framework_bp = Blueprint('framework', __name__)

@framework_bp.route('/generate-framework', methods=['POST'])
def generate_framework_route():
    data = request.get_json()
    gioia_text = data.get('gioia_text')
    if not gioia_text:
        return jsonify({'error': 'Missing gioia_text'}), 400
    output_id = str(uuid.uuid4())
    output_path = os.path.join('outputs', f'framework_{output_id}')
    image_path = generate_framework(gioia_text, output_path)
    return jsonify({'image_path': image_path}) 