from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .models import User

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
settings = get_settings()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hash.verify(password, hashed)
    except Exception:
        return False


def create_token(user: User) -> str:
    return jwt.encode({'sub': str(user.id), 'exp': datetime.now(timezone.utc) + timedelta(hours=24)}, settings.secret_key, algorithm='HS256')


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Sign in required')
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=['HS256'])
        uid = int(payload['sub'])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Session expired or invalid')
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Account not found')
    return user


def role_guard(role: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role != role:
            raise HTTPException(403, 'Not authorized for this operation')
        return user
    return guard
