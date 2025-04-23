from flask import Blueprint, request, jsonify
import logging

from func.models.user import User
from func.models.media import Media
from func.oauth_utils import generate_jwt_token, decode_jwt_token, token_required
from func.utils import validate_username, validate_email, validate_password
from func.constants import USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH

user_bp = Blueprint('user', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)

@user_bp.route('/register', methods=['POST'])
def register():
    from func.models.user_embedding import UserEmbedding  # Import UserEmbedding here to avoid circular imports
    from scripts.ollama import text_to_embedding 
    data = request.get_json()

    required_fields = ['username', 'email', 'password', 'confirm_password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    username = data['username']
    email = data['email']
    bio = data.get('bio')
    avatar_id = data.get('avatar_id')
    password = data['password']
    confirm_password = data['confirm_password']
    is_private = data.get('is_private', False)

    if len(username) < USERNAME_MIN_LENGTH or len(username) > USERNAME_MAX_LENGTH:
        return jsonify({'error': 'Username length invalid'}), 400

    if not validate_username(username):
        return jsonify({'error': 'Username contains invalid characters'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    success, errors = validate_password(password)
    if not success:
        return jsonify({'error': errors}), 400

    try:
        if User.get(username=username) or User.get(email=email):
            return jsonify({'error': 'Username or email already exists'}), 409

        user = User.create(
            username=username,
            email=email,
            password=password,
            bio=bio,
            avatar=Media.get(avatar_id) if avatar_id else None,
            is_private=is_private
        )
         # Generate and save the embedding for the new user
        user_text = f"{bio or ''}"  # Use the bio or an empty string if bio is None
        embedding = text_to_embedding(user_text)  # Generate the embedding using the text_to_embedding function
         # Save the embedding to the user_embedding table
        try:
            UserEmbedding.create(user_id=user.id, embedding=embedding.tolist())
        except Exception as e:
            print (e)

        return jsonify({
            'user': user.to_dict(),
            'access_token': generate_jwt_token(user.id),
            'refresh_token': generate_jwt_token(user.id, is_refresh=True)
        }), 201

    except Exception as e:
        print (str(e))
        logger.error(f"Error during registration: {str(e)}")
        return jsonify({'error': 'Server error during registration'}), 500

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Login and password are required'}), 400

    try:
        user = User.authenticate(data.get('username'), data.get('password'))

        if not user:
            return jsonify({'error': 'Invalid login credentials'}), 401

        return jsonify({
            'user': user.to_dict(include_private=True),
            'access_token': generate_jwt_token(user.id),
            'refresh_token': generate_jwt_token(user.id, is_refresh=True)
        }), 200

    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return jsonify({'error': 'Server error during login'}), 500

@user_bp.route('/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json()
    if not data.get('refresh_token'):
        return jsonify({'error': 'Refresh token required'}), 400

    try:
        payload = decode_jwt_token(data['refresh_token'])

        if not payload or payload.get('type') != 'refresh':
            return jsonify({'error': 'Invalid or expired token'}), 401

        user = User.get(id=payload['sub'])

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'access_token': generate_jwt_token(user.id),
            'refresh_token': generate_jwt_token(user.id, is_refresh=True)
        }), 200

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Server error during token refresh'}), 500

@user_bp.route('/username/check', methods=['GET'])
def check_username():
    username = request.args.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    if len(username) < USERNAME_MIN_LENGTH:
        return jsonify({'available': False, 'message': f'Username must be at least {USERNAME_MIN_LENGTH} characters long'}), 200

    if not validate_username(username):
        return jsonify({'available': False, 'message': 'Invalid characters in username'}), 200

    try:
        if User.username_exists(username):
            return jsonify({'available': False, 'message': 'Username is taken'}), 200
        return jsonify({'available': True, 'message': 'Username is available'}), 200

    except Exception as e:
        logger.error(f"Username check error: {str(e)}")
        return jsonify({'error': 'Server error'}), 500