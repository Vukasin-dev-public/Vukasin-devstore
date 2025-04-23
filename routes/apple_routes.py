from flask import Blueprint, request, jsonify
import json
import jwt
import logging

from func.models.user import User
from func.oauth_utils import generate_jwt_token
from func.constants import APPLE_CLIENT_ID

apple_bp = Blueprint('apple', __name__, url_prefix='/apple')
logger = logging.getLogger(__name__)

@apple_bp.route('/auth', methods=['POST'])
def apple_auth():
    data = request.get_json()

    if not data.get('id_token'):
        return jsonify({'error': 'Apple ID token is required'}), 400

    try:
        token_parts = data['id_token'].split('.')
        if len(token_parts) != 3:
            return jsonify({'error': 'Invalid token format'}), 401

        payload = json.loads(token_parts[1] + '==')  # padding for base64

        if payload.get('iss') != 'https://appleid.apple.com':
            return jsonify({'error': 'Invalid token issuer'}), 401

        if payload.get('aud') != APPLE_CLIENT_ID:
            return jsonify({'error': 'Invalid token audience'}), 401

        apple_id = payload.get('sub')
        email = payload.get('email')

        if not apple_id:
            return jsonify({'error': 'Invalid Apple ID token'}), 401

        user = User.authenticate_with_apple(apple_id, email)

        if not user:
            return jsonify({'error': 'Failed to authenticate with Apple'}), 401

        access_token = generate_jwt_token(user.id)
        refresh_token = generate_jwt_token(user.id, is_refresh=True)

        return jsonify({
            'user': user.to_dict(include_private=True),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid Apple token'}), 401
    except Exception as e:
        logger.error(f"Error during Apple authentication: {str(e)}")
        return jsonify({'error': 'Server error during Apple authentication'}), 500
