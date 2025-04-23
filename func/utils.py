from func.constants import USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH

import re
import hashlib
import secrets
from uuid import uuid4
from json import dump, load, JSONDecodeError
from typing import List, Tuple
import random
import string

def save_json(data: dict | list, filename: str = "data.json"):
    if not filename.endswith(".json"):
        filename += ".json"
        
    try:
        with open(filename, "w") as f:
            dump(data, f, indent=4)
    except IOError as e:
        print(f"An error occurred while saving the file: {e}")

def load_json(filename: str = "data.json"):
    if not filename.endswith(".json"):
        filename += ".json"

    try:
        with open(filename, "r") as f:
            data = load(f)
    except (FileNotFoundError, JSONDecodeError):
        data = {}
    return data

# Default settings (used if constants aren't defined)
try:
    from func.constants import (
        PASSWORD_MIN_LENGTH,
        PASSWORD_REQUIRE_UPPERCASE,
        PASSWORD_REQUIRE_LOWERCASE,
        PASSWORD_REQUIRE_NUMBER,
        PASSWORD_REQUIRE_SPECIAL,
    )
except ImportError:
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBER = True
    PASSWORD_REQUIRE_SPECIAL = True


def generate_unique_id():
    """Generate a unique UUID string"""
    return str(uuid4())

def generate_random_string(
    length: int = 16,
    include_numbers: bool = True,
    include_ascii_letters: bool = True,
    include_special_chars: bool = False
) -> str:
    chars = ''
    
    if include_numbers:
        chars += string.digits
    if include_ascii_letters:
        chars += string.ascii_letters
    if include_special_chars:
        chars += string.punctuation

    if not chars:
        raise ValueError("At least one character set must be included.")
    
    return ''.join(random.choice(chars) for _ in range(length))


def hash_password(password):
    """Hash a password using SHA-256 with a secure salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${password_hash}"


def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    if not hashed_password:
        return False
    
    try:
        salt, stored_hash = hashed_password.split('$')
    except ValueError:
        return False

    computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return secrets.compare_digest(computed_hash, stored_hash)


def validate_password(password) -> Tuple[bool, List[str]]:
    """Validate password strength based on defined requirements"""
    success, errors = True, []
    if len(password) < PASSWORD_MIN_LENGTH:
        success = False
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")

    if PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        success = False
        errors.append("Password must contain at least one uppercase letter.")

    if PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        success = False
        errors.append("Password must contain at least one lowercase letter.")

    if PASSWORD_REQUIRE_NUMBER and not any(c.isdigit() for c in password):
        success = False
        errors.append("Password must contain at least one number.")

    if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        success = False
        errors.append("Password must contain at least one special character.")

    return success, errors

def validate_email(email):
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def validate_username(username) -> Tuple[bool, List[str]]:
    """Validate username format"""
    success, errors = True, []
    
    if len(username) < USERNAME_MIN_LENGTH:
        success = False 
        errors.append(f'Username must be at least {USERNAME_MIN_LENGTH} characters long.')
        
    if len(username) > USERNAME_MAX_LENGTH:
        success = False 
        errors.append(f'Username cannot exceed {USERNAME_MAX_LENGTH} characters.')
        
    if not re.match(r'^[a-zA-Z0-9_.]+$', username):
        success = False 
        errors.append('Username can only contain letters, numbers, underscores, and periods.')
    
    return success, errors