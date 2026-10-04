"""Repository link validation and GitHub/GitLab API lookups (no database access)."""
from urllib.parse import quote, urlparse

import httpx
from fastapi import HTTPException

from .config import GITHUB_TOKEN

HOSTS = {"github.com", "gitlab.com"}
TIMEOUT = 8.0


def parse_repo_url(raw: str) -> tuple[str, str]:
    """Return (host, 'owner/repo') or raise ValueError. Only GitHub and GitLab are accepted."""
    url = urlparse(raw.strip())
    host = (url.hostname or "").removeprefix("www.")
    if url.scheme != "https" or host not in HOSTS:
        raise ValueError("Repository link must be an https://github.com or https://gitlab.com URL")
    parts = [p for p in url.path.split("/") if p]
    if host == "gitlab.com" and "-" in parts:  # drop /-/tree/main style suffixes
        parts = parts[: parts.index("-")]
    if host == "github.com":
        parts = parts[:2]
    if len(parts) < 2:
        raise ValueError("Repository link must point at a repository, e.g. https://github.com/owner/repo")
    parts[-1] = parts[-1].removesuffix(".git")
    return host, "/".join(parts)


def canonical_repo_url(raw: str) -> str:
    host, path = parse_repo_url(raw)
    return f"https://{host}/{path}"


def needs_from_languages(langs: dict[str, float]) -> dict[str, float]:
    """Turn language shares into skill levels: >=50% -> 4, >=20% -> 3, >=5% -> 2."""
    total = sum(langs.values()) or 1
    needs: dict[str, float] = {}
    for name, size in sorted(langs.items(), key=lambda kv: -kv[1])[:5]:
        share = size / total
        if share >= 0.05:
            needs[name.lower()] = 4 if share >= 0.5 else 3 if share >= 0.2 else 2
    return needs


def _get(client: httpx.Client, url: str, **kw):
    try:
        res = client.get(url, timeout=TIMEOUT, **kw)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Could not reach the code host. Try again in a moment.") from exc
    if res.status_code == 404:
        raise HTTPException(404, "Repository not found. Check the link and that it is public.")
    if res.status_code in (403, 429):
        raise HTTPException(503, "The code host rate limit was reached. Try again later.")
    if res.status_code >= 400:
        raise HTTPException(502, f"Code host returned {res.status_code}")
    return res.json()


def _github_headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def inspect_repo(raw: str) -> dict:
    """Fetch title, description, suggested needs and tags, and stars for a repo link."""
    host, path = parse_repo_url(raw)
    with httpx.Client() as c:
        if host == "github.com":
            base = f"https://api.github.com/repos/{path}"
            info = _get(c, base, headers=_github_headers())
            langs = _get(c, base + "/languages", headers=_github_headers())
            return {
                "repo_url": f"https://github.com/{path}",
                "title": info.get("name") or path.split("/")[-1],
                "description": info.get("description"),
                "needs": needs_from_languages(langs),
                "tags": [t.lower() for t in info.get("topics", [])][:8],
                "stars": info.get("stargazers_count", 0),
            }
        base = f"https://gitlab.com/api/v4/projects/{quote(path, safe='')}"
        info = _get(c, base)
        langs = _get(c, base + "/languages")  # already percentages
        return {
            "repo_url": f"https://gitlab.com/{path}",
            "title": info.get("name") or path.split("/")[-1],
            "description": info.get("description"),
            "needs": needs_from_languages(langs),
            "tags": [t.lower() for t in info.get("topics", [])][:8],
            "stars": info.get("star_count", 0),
        }


def infer_skills(login: str) -> dict[str, float]:
    """Guess a new user's skills from their public repos: level = 1 + repos // 2, capped at 5."""
    try:
        with httpx.Client() as c:
            repos = _get(c, f"https://api.github.com/users/{login}/repos?per_page=100&sort=pushed",
                         headers=_github_headers())
    except HTTPException:
        return {}
    counts: dict[str, int] = {}
    for r in repos:
        if r.get("language") and not r.get("fork"):
            counts[r["language"].lower()] = counts.get(r["language"].lower(), 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:6]
    return {lang: min(5, 1 + n // 2) for lang, n in top}
