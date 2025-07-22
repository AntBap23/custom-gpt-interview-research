from flask import Blueprint, request, jsonify, send_file
import os
import zipfile

export_bp = Blueprint('export', __name__)

@export_bp.route('/export-results', methods=['POST'])
def export_results_route():
    data = request.get_json()
    interviewee_id = data.get('interviewee_id')
    if not interviewee_id:
        return jsonify({'error': 'Missing interviewee_id'}), 400
    # Find all files in outputs/ containing the interviewee_id
    output_dir = 'outputs'
    files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if interviewee_id in f]
    if not files:
        return jsonify({'error': 'No files found for this ID'}), 404
    zip_path = os.path.join(output_dir, f'{interviewee_id}.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    return send_file(zip_path, as_attachment=True) 