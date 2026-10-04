import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"

from urllib.parse import parse_qs, urlparse

import httpx
from fastapi.testclient import TestClient
from src.backend import repos
from src.backend.auth import make_token
from src.backend.main import app
from src.backend.database import SessionLocal
from src.backend.models import Developer

client = TestClient(app)


def test_github_login_redirect(monkeypatch):
    import src.backend.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_ID", "test-client")
    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(auth_router, "PUBLIC_API_URL", "https://backend.ifamished.com")

    response = client.get("/auth/github/login", follow_redirects=False)

    assert response.status_code == 307
    redirect = urlparse(response.headers["location"])
    query = parse_qs(redirect.query)
    assert redirect.netloc == "github.com"
    assert query["client_id"] == ["test-client"]
    assert query["redirect_uri"] == ["https://backend.ifamished.com/auth/github/callback"]
    auth_router.read_token(query["state"][0], purpose="state")


def test_github_login_requires_client_secret(monkeypatch):
    import src.backend.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_ID", "test-client")
    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_SECRET", "")

    assert client.get("/auth/github/login").status_code == 503


def test_github_callback_redirects_to_frontend(monkeypatch):
    import src.backend.routers.auth as auth_router

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, url, *, json, headers):
            assert url == "https://github.com/login/oauth/access_token"
            assert json["code"] == "oauth-code"
            assert headers["Accept"] == "application/json"
            return FakeResponse({"access_token": "github-token"})

        def get(self, url, *, headers):
            assert url == "https://api.github.com/user"
            assert headers["Authorization"].startswith("Bearer ")
            assert headers["Authorization"].endswith("github-token")
            return FakeResponse({
                "id": 70001,
                "login": "callback-user",
                "name": "Callback User",
                "avatar_url": None,
            })

    def fake_infer_skills(login):
        assert login == "callback-user"
        return {"python": 3}

    def build_client(*, timeout):
        assert timeout == 10
        return FakeClient()

    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_ID", "test-client")
    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(auth_router, "FRONTEND_URL", "https://patchwork.millered001.workers.dev")
    monkeypatch.setattr(auth_router, "infer_skills", fake_infer_skills)
    monkeypatch.setattr(auth_router.httpx, "Client", build_client)
    state = make_token("oauth", purpose="state", ttl=600)

    response = client.get(
        "/auth/github/callback",
        params={"code": "oauth-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 307
    redirect = urlparse(response.headers["location"])
    assert redirect.scheme == "https"
    assert redirect.netloc == "patchwork.millered001.workers.dev"
    assert redirect.path == "/"
    callback_params = parse_qs(redirect.fragment.split("?", 1)[1])
    assert auth_router.read_token(callback_params["token"][0])


def mock_transport(request: httpx.Request) -> httpx.Response:
    u = str(request.url)
    if u.endswith("/repos/o/good"):
        return httpx.Response(200, json={"name": "good", "description": "d", "topics": ["Data"], "stargazers_count": 7})
    if u.endswith("/repos/o/good/languages"):
        return httpx.Response(200, json={"Python": 8000, "SQL": 1500, "Makefile": 100})
    if "/gitlab" in u or "gitlab.com" in u:
        return httpx.Response(200, json={"Go": 90.0, "Shell": 10.0} if u.endswith("languages") else {"name": "g", "topics": [], "star_count": 1})
    return httpx.Response(404, json={})


_Real = httpx.Client
repos.httpx.Client = lambda **kw: _Real(transport=httpx.MockTransport(mock_transport), **kw)


def user(gid, login):
    with SessionLocal() as db:
        d = Developer(github_id=gid, login=login, name=login, skills={}, interests=[])
        db.add(d); db.commit()
        return {"Authorization": f"Bearer {make_token(str(d.id))}"}, d.id


def test_flow():
    a, aid = user(1, "alice"); b, _ = user(2, "bob")
    assert client.get("/feed").status_code == 401
    assert client.put("/me", json={"name": "Alice A", "skills": {"Python ": 4}, "interests": ["Data"]}, headers=a).json()["skills"] == {"python": 4}

    info = client.get("/repo/inspect", params={"url": "https://github.com/o/good"}, headers=a).json()
    assert info["needs"] == {"python": 4, "sql": 2} and info["tags"] == ["data"]
    assert client.get("/repo/inspect", params={"url": "https://github.com/o/nope"}, headers=a).status_code == 404
    assert client.get("/repo/inspect", params={"url": "https://bitbucket.org/o/x"}, headers=a).status_code == 422

    body = {"title": "Good", "repo_url": "https://github.com/o/good.git", "needs": {"Python": 4, "sql": 2}, "tags": ["Data", "web"]}
    assert client.post("/project", json=body).status_code == 401
    assert client.post("/project", json={**body, "repo_url": "https://evil.com/o/good"}, headers=b).status_code == 422
    assert client.post("/project", json={**body, "video_url": "http://x.com/a.mp4"}, headers=b).status_code == 422
    assert client.post("/project", json={**body, "repo_url": "https://github.com/o/nope"}, headers=b).status_code == 404
    p = client.post("/project", json=body, headers=b)
    assert p.status_code == 201 and p.json()["repo_url"] == "https://github.com/o/good", p.text
    pid = p.json()["id"]

    f = client.get("/feed", headers=a).json()
    # skill_fit = (4/4 + 2/2)/2 + ... alice has python 4, no sql => (1+0)/2 = .5 ; interest 1/2 => .5*.75+.5*.25
    assert f[0]["skill_fit"] == 0.5 and f[0]["interest_fit"] == 0.5 and f[0]["match_score"] == 0.5
    assert client.get("/feed", headers=b).json() == []  # own project hidden

    assert client.post("/swipe", json={"project_id": pid, "action": "APPLY"}, headers=b).status_code == 400
    assert client.post("/swipe", json={"project_id": pid, "action": "APPLY"}, headers=a).status_code == 201
    assert client.post("/swipe", json={"project_id": pid, "action": "LIKE"}, headers=a).status_code == 409
    assert client.get("/feed", headers=a).json() == []
    assert [x["id"] for x in client.get("/me/applications", headers=a).json()] == [pid]
    assert client.post("/match", json={"developer_id": aid, "project_id": pid}, headers=b).status_code == 200
    c, _ = user(3, "carol")
    assert client.post("/match", json={"developer_id": aid, "project_id": pid}, headers=c).status_code == 403

    assert client.put(f"/project/{pid}", json={"title": "X"}, headers=a).status_code == 403
    assert client.delete(f"/project/{pid}", headers=a).status_code == 403
    assert client.put(f"/project/{pid}", json={"title": "Better", "needs": {"go": 2}}, headers=b).json()["needs"] == {"go": 2}
    assert client.delete(f"/project/{pid}", headers=b).status_code == 204
    assert client.get(f"/project/{pid}").status_code == 404
    assert client.get("/me/applications", headers=a).json() == []


def test_upload_limits():
    a, _ = user(9, "up")
    assert client.post("/upload_video", files={"file": ("x.mov", b"1")}, headers=a).status_code == 415
    assert client.post("/upload_video", files={"file": ("x.mp4", b"1")}).status_code == 401
    r = client.post("/upload_video", files={"file": ("x.mp4", b"1234")}, headers=a)
    assert r.status_code == 200 and r.json()["video_url"].endswith(".mp4")
    import src.backend.routers.project as pr
    pr.MAX_VIDEO_BYTES = 2
    assert client.post("/upload_video", files={"file": ("x.mp4", b"1234")}, headers=a).status_code == 413
