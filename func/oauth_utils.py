import jwt
import datetime
from functools import wraps
from flask import request, jsonify
from func.constants import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES, JWT_REFRESH_TOKEN_EXPIRES, ADMIN_TOKEN


def generate_jwt_token(user_id, is_refresh=False):
    """Generate a JWT token for a user"""
    now = datetime.datetime.utcnow()
    
    expires_delta = datetime.timedelta(
        seconds=JWT_REFRESH_TOKEN_EXPIRES if is_refresh else JWT_ACCESS_TOKEN_EXPIRES
    )
    
    payload = {
        'sub': str(user_id),
        'iat': now,
        'exp': now + expires_delta,
        'type': "refresh" if is_refresh else "access"
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    return token


def decode_jwt_token(token):
    """Decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require a valid JWT token for access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Authentication token is missing'}), 401

        payload = decode_jwt_token(token)
        if not payload:
            return jsonify({'message': 'Invalid or expired token'}), 401

        if payload.get('type') != 'access':
            return jsonify({'message': 'Invalid token type'}), 401

        kwargs['user_id'] = payload['sub']
        return f(*args, **kwargs)

    return decorated

# Auth decorator for admin endpoints
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_token = request.args.get('admin_token')
        if not admin_token or admin_token != ADMIN_TOKEN:  # Implement your token validation
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

def inject_admin_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_token = request.args.get('admin_token')
        kwargs['admin_request'] = admin_token == ADMIN_TOKEN
        return f(*args, **kwargs)
    return decorated