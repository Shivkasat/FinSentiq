import os
import time
import json
import hmac
import hashlib
import base64
import secrets
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger("finsentiq.security")

def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${dk.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if "$" not in hashed_password:
            return plain_password == hashed_password
        salt, dk_hex = hashed_password.split("$", 1)
        test_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return hmac.compare_digest(test_dk.hex(), dk_hex)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta_seconds: Optional[int] = None) -> str:
    secret = settings.SECRET_KEY.encode("utf-8")
    header_json = json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8")
    header_b64 = base64.urlsafe_b64encode(header_json).decode("utf-8").rstrip("=")

    payload = data.copy()
    exp_time = int(time.time()) + (expires_delta_seconds or (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))
    payload["exp"] = exp_time
    payload_json = json.dumps(payload).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")

    signature = hmac.new(secret, f"{header_b64}.{payload_b64}".encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts

        secret = settings.SECRET_KEY.encode("utf-8")
        expected_sig = hmac.new(secret, f"{h_b64}.{p_b64}".encode("utf-8"), hashlib.sha256).digest()
        
        # Add padding back if necessary
        padded_s = s_b64 + "=" * (-len(s_b64) % 4)
        actual_sig = base64.urlsafe_b64decode(padded_s.encode("utf-8"))

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        padded_p = p_b64 + "=" * (-len(p_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_p.encode("utf-8")).decode("utf-8"))

        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None
