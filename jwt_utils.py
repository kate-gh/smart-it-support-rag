# jwt_utils.py
import os

from flask.cli import load_dotenv

import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = "HS256"
EXPIRY_H   = 1

def create_token(user_id: str, username: str, role: str) -> str:
    return jwt.encode({
        "user_id" : user_id,
        "username": username,
        "role"    : role,
        "exp"     : datetime.utcnow() + timedelta(hours=EXPIRY_H),
        "iat"     : datetime.utcnow(),
    }, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def _get_payload() -> dict | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return decode_token(auth.split(" ", 1)[1])

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        payload = _get_payload()
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        payload = _get_payload()
        if not payload:
            return jsonify({"error": "unauthorized"}), 401
        if payload.get("role") != "admin":
            return jsonify({"error": "admin required"}), 403
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated