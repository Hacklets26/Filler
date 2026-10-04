import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"
os.environ["JWT_SECRET"] = "test-only-secret-for-patchwork-tests-32"

from urllib.parse import parse_qs, urlparse

import httpx
from fastapi.testclient import TestClient
from src.backend import repos
from src.backend.auth import make_token
from src.backend.main import app
from src.backend.database import SessionLocal
from src.backend.models import Developer

client = TestClient(app)


def test_app_launcher_from_backend_root():
    backend_root = Path(__file__).resolve().parents[1] / "src" / "backend"
    launcher_check = (
        "import runpy, uvicorn\n"
        "def record_run(application, **options):\n"
        "    assert options == {'host': '0.0.0.0', 'port': 30007}\n"
        "    print('launcher invoked')\n"
        "uvicorn.run = record_run\n"
        "runpy.run_path('app.py', run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", launcher_check],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "launcher invoked" in result.stdout


def test_backend_refuses_missing_or_insecure_jwt_secrets():
    for secret in (None, "too-short", "replace-with-random-secret-at-least-32-characters-long",
                   "patchwork-development-secret-change-before-deploy"):
        env = os.environ.copy()
        if secret is None:
            env.pop("JWT_SECRET", None)
        else:
            env["JWT_SECRET"] = secret
        result = subprocess.run(
            [sys.executable, "-c", "from src.backend.config import JWT_SECRET"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0
        assert "JWT_SECRET" in result.stderr


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


def test_github_login_reports_conflicting_jwt_package(monkeypatch):
    import src.backend.auth as backend_auth
    import src.backend.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_ID", "test-client")
    monkeypatch.setattr(auth_router, "GITHUB_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(backend_auth.jwt, "encode", None)

    response = client.get("/auth/github/login")

    assert response.status_code == 503
    assert "uninstall the conflicting 'jwt' package" in response.json()["detail"]


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


def test_match_uses_only_available_signals_and_weights_skill_demand():
    from src.backend.matching import explain_match
    from src.backend.models import Project

    developer = Developer(
        github_id=5, login="ada", name="Ada", skills={"Python": 5}, interests=[],
    )
    project = Project(
        title="Garden", description="A small project", repo_url="https://github.com/o/garden",
        needs={"python": 5, "sql": 1}, tags=[], maintainer_id=8,
    )

    result = explain_match(developer, project)

    assert result == {
        "match_score": 0.6667,
        "skill_fit": 0.8333,
        "interest_fit": None,
        "text_fit": 0,
        "interest_relevance_fit": 0,
    }

    project.needs = {}
    developer.skills = {}
    assert explain_match(developer, project) == {
        "match_score": 0.5,
        "skill_fit": None,
        "interest_fit": None,
        "text_fit": None,
        "interest_relevance_fit": None,
    }


def test_interest_relevance_fit_combines_available_signals_without_changing_match_score():
    from src.backend.matching import explain_match
    from src.backend.models import Project

    developer = Developer(
        github_id=7,
        login="ada",
        name="Ada",
        skills={"python": 5},
        interests=["data", "design"],
    )
    project = Project(
        title="Python data",
        description=None,
        repo_url="https://github.com/o/data",
        needs={"python": 5},
        tags=["data", "web"],
        maintainer_id=8,
    )

    result = explain_match(developer, project)

    assert result["skill_fit"] == 1
    assert result["interest_fit"] == 0.5
    assert result["text_fit"] == 0.6667
    assert result["interest_relevance_fit"] == 0.5625
    assert result["match_score"] == 0.825

    project.tags = []
    text_only = explain_match(developer, project)
    assert text_only["interest_fit"] is None
    assert text_only["interest_relevance_fit"] == text_only["text_fit"]

    project.title = ""
    project.description = None
    no_relevance_data = explain_match(developer, project)
    assert no_relevance_data["interest_relevance_fit"] is None


def test_text_fit_matches_profile_phrases_across_punctuation_and_stop_words():
    from src.backend.matching import explain_match
    from src.backend.models import Project

    developer = Developer(
        github_id=6,
        login="grace",
        name="Grace",
        skills={"Machine Learning": 3},
        interests=["Build"],
    )
    project = Project(
        title="Machine-Learning Build",
        description=None,
        repo_url="https://github.com/o/ml",
        needs={},
        tags=[],
        maintainer_id=8,
    )

    assert explain_match(developer, project)["text_fit"] == 1


def test_project_update_does_not_delete_video_before_commit(monkeypatch):
    import pytest
    from src.backend.models import Project
    from src.backend.routers import project as project_router
    from src.backend.schemas import ProjectUpdate

    old_video_url = f"https://backend.test/videos/{'a' * 32}.mp4"
    project = Project(
        id=10,
        title="Existing",
        repo_url="https://github.com/o/existing",
        video_url=old_video_url,
        needs={},
        tags=[],
        maintainer_id=8,
    )
    maintainer = Developer(
        id=8, github_id=8, login="maintainer", name="Maintainer", skills={}, interests=[],
    )

    database = SessionLocal()
    deleted_urls = []

    def get_project(model, project_id):
        assert model is Project
        assert project_id == project.id
        return project

    monkeypatch.setattr(database, "get", get_project)

    def fail_commit():
        raise RuntimeError("Database commit failed")

    monkeypatch.setattr(database, "commit", fail_commit)
    monkeypatch.setattr(project_router, "delete_video_file", deleted_urls.append)
    with pytest.raises(RuntimeError, match="Database commit failed"):
        project_router.update_project(
            10, ProjectUpdate(video_url=None), maintainer, database,
        )

    database.close()
    assert deleted_urls == []


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
    assert f[0]["skill_fit"] == 0.6667
    assert f[0]["interest_fit"] == 0.5
    assert f[0]["text_fit"] == 0
    assert f[0]["interest_relevance_fit"] == 0.3125
    assert f[0]["match_score"] == 0.525
    assert client.get("/feed", headers=b).json() == []  # own project hidden

    assert client.post("/swipe", json={"project_id": pid, "action": "APPLY"}, headers=b).status_code == 400
    assert client.post("/swipe", json={"project_id": pid, "action": "APPLY"}, headers=a).status_code == 201
    assert client.post("/swipe", json={"project_id": pid, "action": "LIKE"}, headers=a).status_code == 422
    assert client.get("/feed", headers=a).json() == []
    sent = client.get("/me/applications", headers=a).json()
    assert len(sent) == 1 and sent[0]["project"]["id"] == pid and sent[0]["status"] == "pending"
    incoming = client.get("/me/incoming-applications", headers=b).json()
    assert len(incoming) == 1 and incoming[0]["developer"]["login"] == "alice"
    assert incoming[0]["status"] == "pending"
    c, _ = user(3, "carol")
    assert client.put(f"/applications/{sent[0]['application_id']}", json={"status": "accepted"}, headers=c).status_code == 403
    assert client.put(f"/applications/{sent[0]['application_id']}", json={"status": "accepted"}, headers=b).status_code == 200
    assert client.get("/me/applications", headers=a).json()[0]["status"] == "accepted"
    assert client.post("/match", json={"developer_id": aid, "project_id": pid}, headers=b).status_code == 200
    assert client.post("/match", json={"developer_id": aid, "project_id": pid}, headers=c).status_code == 403

    assert client.put(f"/project/{pid}", json={"title": "X"}, headers=a).status_code == 403
    assert client.delete(f"/project/{pid}", headers=a).status_code == 403
    assert client.put(f"/project/{pid}", json={"title": "Better", "needs": {"go": 2}}, headers=b).json()["needs"] == {"go": 2}
    assert client.delete(f"/project/{pid}", headers=b).status_code == 204
    from src.backend.models import ApplicationReview
    with SessionLocal() as database:
        assert database.get(ApplicationReview, sent[0]["application_id"]) is None
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
