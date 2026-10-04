from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import make_token, read_token
from ..config import FRONTEND_URL, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, PUBLIC_API_URL
from ..database import get_db
from ..models import Developer
from ..repos import infer_skills

router = APIRouter(tags=["auth"])


@router.get("/auth/github/login")
def github_login():
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(503, "GitHub login is not configured on the server")
    state = make_token("oauth", purpose="state", ttl=600)
    query = urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "scope": "read:user",
        "state": state,
        "redirect_uri": f"{PUBLIC_API_URL}/auth/github/callback",
    })
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")


@router.get("/auth/github/callback")
def github_callback(code: str, state: str, database: Session = Depends(get_db)):
    read_token(state, purpose="state")  # rejects forged or expired state
    try:
        with httpx.Client(timeout=10) as client:
            token = client.post(
                "https://github.com/login/oauth/access_token",
                json={"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "code": code},
                headers={"Accept": "application/json"},
            ).json().get("access_token")
            if not token:
                raise HTTPException(400, "GitHub rejected the login code")
            gh = client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"}).json()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Could not reach GitHub") from exc

    developer = database.scalar(select(Developer).where(Developer.github_id == gh["id"]))
    if developer is None:
        developer = Developer(
            github_id=gh["id"], login=gh["login"], name=gh.get("name") or gh["login"],
            avatar_url=gh.get("avatar_url"), skills=infer_skills(gh["login"]), interests=[],
        )
        database.add(developer)
    else:
        developer.login, developer.avatar_url = gh["login"], gh.get("avatar_url")
    database.commit()
    return RedirectResponse(f"{FRONTEND_URL}/#/auth?token={make_token(str(developer.id))}")
