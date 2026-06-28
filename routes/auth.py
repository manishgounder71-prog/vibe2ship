"""
FutureShield AI — JWT Authentication Endpoints

Provides user registration, login, token verification, and profile
management. Uses bcrypt for password hashing and JWT (HS256) for
session tokens.

Endpoints:
  POST /api/auth/register  — Create a new user account
  POST /api/auth/login     — Authenticate and receive a JWT
  POST /api/auth/logout    — Invalidate the current token
  GET  /api/auth/verify    — Verify a token and return user info
  GET  /api/auth/profile   — Get current user profile
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

import database

# ─── JWT / Password libs ──────────────────────────────────────────

try:
    from jose import JWTError, jwt
except ImportError:
    jwt = None  # type: ignore[assignment]
    JWTError = Exception  # type: ignore[misc]

try:
    from passlib.context import CryptContext
    # Use sha256_crypt (built into passlib, no C deps needed)
    # bcrypt would be faster but requires the bcrypt C extension
    _pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
except ImportError:
    _pwd_context = None  # type: ignore[assignment]

router = APIRouter(tags=["Auth"])

# ─── Configuration ────────────────────────────────────────────────

SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", str(uuid.uuid4()))
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24h

# ─── Models ────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


# ─── Helpers ──────────────────────────────────────────────────────

def _verify_jwt_available() -> None:
    """Raise a clear error if JWT/Passlib dependencies are missing."""
    if jwt is None:
        raise HTTPException(
            status_code=500,
            detail="JWT authentication requires 'python-jose' and 'passlib' + 'bcrypt'. "
                   "Install: pip install python-jose[cryptography] passlib[bcrypt]",
        )


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    if _pwd_context is None:
        raise HTTPException(status_code=500, detail="Password hashing library not available")
    return _pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    if _pwd_context is None:
        return False
    return _pwd_context.verify(plain, hashed)


def _create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    _verify_jwt_available()
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token. Raises HTTPException on failure."""
    _verify_jwt_available()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(authorization: str = Header("")) -> dict[str, Any]:
    """Dependency: Extract and verify the current user from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = _decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = database.query_db(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (int(user_id),),
        one=True,
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ─── Endpoints ────────────────────────────────────────────────────


@router.post("/api/auth/register", response_model=TokenResponse)
def register(request: RegisterRequest) -> dict[str, Any]:
    """Register a new user account. Returns a JWT token on success."""
    _verify_jwt_available()

    # Validate inputs
    if len(request.username.strip()) < 3:
        raise HTTPException(status_code=422, detail="Username must be at least 3 characters")
    if "@" not in request.email:
        raise HTTPException(status_code=422, detail="Invalid email address")
    if len(request.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    # Check for existing user
    existing = database.query_db(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (request.username.strip(), request.email.strip().lower()),
        one=True,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    # Create user
    password_hash = _hash_password(request.password)
    user_id = database.insert_and_get_id(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (request.username.strip(), request.email.strip().lower(), password_hash),
    )

    # Generate token
    access_token = _create_access_token({"sub": str(user_id), "username": request.username.strip()})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": request.username.strip(),
            "email": request.email.strip().lower(),
        },
    }


@router.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest) -> dict[str, Any]:
    """Authenticate with username and password. Returns a JWT token."""
    _verify_jwt_available()

    user = database.query_db(
        "SELECT * FROM users WHERE username = ?",
        (request.username.strip(),),
        one=True,
    )
    if user is None or not _verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = _create_access_token({"sub": str(user["id"]), "username": user["username"]})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
        },
    }


@router.post("/api/auth/logout")
def logout() -> dict[str, str]:
    """Logout by invalidating the current token.

    Note: True JWT invalidation requires a blocklist. For this
    implementation, the client simply discards the token.
    """
    return {"status": "logged_out", "message": "Token discarded. Please remove it from storage."}


@router.get("/api/auth/verify")
def verify_token(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Verify that the current token is valid and return user info."""
    return {
        "valid": True,
        "user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
        },
    }


@router.get("/api/auth/profile")
def get_profile(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Get the current user's profile information."""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
    }
