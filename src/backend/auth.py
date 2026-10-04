import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import JWT_SECRET
from .database import get_db
from .models import Developer

_bearer = HTTPBearer(auto_error=False)


def make_token(subject: str, purpose: str = "session", ttl: int = 7 * 86400) -> str:
    return jwt.encode({"sub": subject, "purpose": purpose, "exp": int(time.time()) + ttl}, JWT_SECRET, "HS256")


def read_token(token: str, purpose: str = "session") -> str:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "Your session expired. Log in again.") from exc
    if data.get("purpose") != purpose:
        raise HTTPException(401, "Invalid token")
    return data["sub"]


def current_developer(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    database: Session = Depends(get_db),
) -> Developer:
    if creds is None:
        raise HTTPException(401, "Log in to continue")
    developer = database.get(Developer, int(read_token(creds.credentials)))
    if developer is None:
        raise HTTPException(401, "Account no longer exists. Log in again.")
    return developer
