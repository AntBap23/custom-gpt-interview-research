from flask import Blueprint, request, jsonify
from stripe_utils import create_checkout_session

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout():
    data = request.get_json()
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    if not user_id or not user_email:
        return jsonify({'error': 'Missing user_id or user_email'}), 400
    url = create_checkout_session(user_id, user_email)
    return jsonify({'checkout_url': url}) 