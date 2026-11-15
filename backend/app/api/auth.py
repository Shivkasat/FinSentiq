import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, Depends, Header
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])
logger = logging.getLogger("finsentiq.api.auth")

USERS_FILE = "backend/data/users.json"

def _resolve_users_file() -> str:
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent.parent  # backend/
    target = base / "data" / "users.json"
    os.makedirs(target.parent, exist_ok=True)
    return str(target)

def _load_users() -> Dict[str, Dict[str, Any]]:
    filepath = _resolve_users_file()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_users(users: Dict[str, Dict[str, Any]]):
    filepath = _resolve_users_file()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    users = _load_users()
    username = req.username.strip()
    email = req.email.strip().lower()

    if not username or len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check duplicates
    for u in users.values():
        if u["username"].lower() == username.lower():
            raise HTTPException(status_code=400, detail="Username is already taken")
        if u["email"].lower() == email:
            raise HTTPException(status_code=400, detail="Email is already registered")

    user_id = f"usr_{abs(hash(username + email))}"
    hashed_pw = get_password_hash(req.password)
    user_record = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": hashed_pw,
        "created_at": datetime.utcnow().isoformat()
    }
    users[user_id] = user_record
    _save_users(users)

    token = create_access_token({"sub": user_id, "username": username, "email": email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": username,
            "email": email
        }
    }

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    users = _load_users()
    identifier = req.username_or_email.strip().lower()

    matched_user = None
    for u in users.values():
        if u["username"].lower() == identifier or u["email"].lower() == identifier:
            matched_user = u
            break

    if not matched_user or not verify_password(req.password, matched_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")

    token = create_access_token({
        "sub": matched_user["id"],
        "username": matched_user["username"],
        "email": matched_user["email"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": matched_user["id"],
            "username": matched_user["username"],
            "email": matched_user["email"]
        }
    }

@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication token required")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    users = _load_users()
    user_id = payload.get("sub")
    user = users.get(user_id)
    if not user:
        # Fallback to payload info
        return {"id": user_id, "username": payload.get("username"), "email": payload.get("email")}

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"]
    }
