# FILLER

FILLER (working name) matches developers with open source projects. Developers log in with GitHub, pitch
projects by repo link, and swipe a feed ranked by how well their skills and interests fit.

To rename it later, search for `FILLER` (case-sensitive); it is the only spelling used.

## Run it

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
cp .env.example .env   # fill in GitHub OAuth credentials, then export them (or use your process manager)
python src/backend/app.py            # API on http://localhost:30007, docs at /docs
cd src/frontend && npm install && npm run dev   # UI on http://localhost:5173
```

Create the OAuth app at <https://github.com/settings/developers> with callback URL
`https://backend.ifamished.com/auth/github/callback`. The deployed UI is
`https://patchwork.millered001.workers.dev` and uses `https://backend.ifamished.com`
as its API by default. For local development, set `PUBLIC_API_URL` to
`http://localhost:30007`, `FRONTEND_URL` to `http://localhost:5173`, and
`VITE_API_BASE` to `http://localhost:30007`.
Tests: `python -m pytest tests`.
Set `JWT_SECRET` to a unique random value of at least 32 characters in every
deployed backend environment; the built-in value is only for local development.

The SQLite database is created by the Python backend from the SQLAlchemy models
when the application starts. It is not checked into Git; local `*.db`, `*.sqlite`,
and `*.sqlite3` files are ignored.

## Auth

`GET /auth/github/login` starts OAuth; the callback creates or finds the developer (new users get skills inferred
from their public repos) and redirects to `FRONTEND_URL/#/auth?token=...`. Send the token as
`Authorization: Bearer <token>` on every other call. The developer is always taken from the token, never the body.

## API (all require a token unless noted)

| Endpoint | Purpose |
|---|---|
| `GET/PUT /me` | Read or update own name, skills, interests |
| `GET /me/projects`, `GET /me/applications` | Own pitches; projects applied to |
| `GET /repo/inspect?url=` | Look up a GitHub/GitLab repo: title, description, suggested needs and tags, stars |
| `POST /project` | Pitch a project (repo must exist and be public) |
| `PUT/DELETE /project/{id}` | Maintainer only. Delete also removes swipes and the video file |
| `GET /project/{id}`, `GET /projects` | Public reads |
| `POST /upload_video` | MP4 only, 50 MB server-side limit |
| `POST /swipe` | `{project_id, action}`; one per project, not on your own projects |
| `POST /match` | Applicant or maintainer, after an `APPLY` |
| `GET /feed` | Ranked projects with `match_score`, `skill_fit`, `interest_fit`; seen and own projects excluded |

## Validation

- `repo_url` must be `https://github.com/...` or `https://gitlab.com/...`; it is canonicalized (no `.git`, no `/tree/...`).
- `video_url` must be a link produced by `/upload_video`.
- Skill levels are 1 to 5; skills and tags are lowercased and de-duplicated server-side.

## Repo lookup

GitHub: `/repos/{owner}/{repo}` and `/languages`. GitLab: `/api/v4/projects/{path}` and `/languages`.
Language share becomes a needed level: at least 50% is 4, 20% is 3, 5% is 2. Topics become tags.
Set `GITHUB_TOKEN` to raise GitHub's limit from 60 to 5,000 requests/hour.

## The match score

```
skill_fit    = mean over needed skills of min(your_level / needed_level, 1)   (1.0 if the project needs nothing)
interest_fit = shared tags / project tags                                      (0.0 if no tags)
score        = 0.75 * skill_fit + 0.25 * interest_fit
```

Explain it as: "you have 80% of what this project needs, and it overlaps 50% with your interests." The feed
cards show both terms as bars. Implementation: `src/backend/matching.py`.
