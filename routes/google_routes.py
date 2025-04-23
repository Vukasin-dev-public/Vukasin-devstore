from flask import Blueprint, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import logging

from func.models.user import User
from func.oauth_utils import generate_jwt_token
from func.constants import GOOGLE_CLIENT_ID

google_bp = Blueprint('google', __name__, url_prefix='/google')
logger = logging.getLogger(__name__)

@google_bp.route('/auth', methods=['POST'])
def google_auth():
    data = request.get_json()

    if not data.get('id_token'):
        return jsonify({'error': 'Google ID token is required'}), 400

    try:
        google_token = data.get('id_token')
        idinfo = id_token.verify_oauth2_token(
            google_token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return jsonify({'error': 'Invalid token issuer'}), 401

        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name')

        user = User.authenticate_with_google(google_id, email, name)

        access_token = generate_jwt_token(user.id)
        refresh_token = generate_jwt_token(user.id, is_refresh=True)

        return jsonify({
            'user': user.to_dict(include_private=True),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    except ValueError as e:
        return jsonify({'error': f'Invalid Google token: {str(e)}'}), 401
    except Exception as e:
        logger.error(f"Error during Google authentication: {str(e)}")
        return jsonify({'error': 'Server error during Google authentication'}), 500
