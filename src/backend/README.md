# FILLER backend

FILLER is a FastAPI service for GitHub sign-in, developer profiles, project
pitches, personalized feeds, applications, and MP4 uploads.

## Install and run

From the repository root:

```bash
python -m pip install -r requirements-dev.txt
python src/backend/app.py
```

The API listens on `http://localhost:30007`; interactive documentation is at
`http://localhost:30007/docs`. The root [README](../../README.md) describes the
frontend and API workflow.

## Configuration

Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` for the GitHub OAuth app.
For the public deployment, register
`https://backend.ifamished.com/auth/github/callback` as its callback URL.
Successful sign-in returns the user to
`https://patchwork.millered001.workers.dev/#/auth?token=...`.

The deployed API and frontend origins are the defaults. For local development,
set `PUBLIC_API_URL=http://localhost:30007`,
`FRONTEND_URL=http://localhost:5173`, and set the frontend build variable
`VITE_API_BASE=http://localhost:30007`. Also set `JWT_SECRET` to a unique random
value of at least 32 characters in deployed environments.

## Database and uploads

The backend creates `src/backend/FILLER.db` and its schema in Python from the
SQLAlchemy models when the application starts. Set `DATABASE_URL` to use another
SQLAlchemy database. SQLite database files are ignored by Git and are not
included in the source checkout.

Uploaded videos are written to `src/backend/videos/` and served from `/videos/`.
Only MP4 files up to 50 MB are accepted.

## API overview

All endpoints below require a bearer token except where indicated.

| Endpoint | Purpose |
|---|---|
| `GET /auth/github/login` | Start GitHub OAuth |
| `GET /auth/github/callback` | Complete OAuth and redirect to the frontend |
| `GET/PUT /me` | Read or update the signed-in developer profile |
| `GET /me/projects`, `GET /me/applications` | List the signed-in developer's projects and applications |
| `GET /repo/inspect?url=...` | Inspect a public GitHub or GitLab repository |
| `POST /project` | Create a project pitch |
| `GET /project/{id}`, `GET /projects` | Read projects (public) |
| `PUT/DELETE /project/{id}` | Update or delete a project as its maintainer |
| `POST /upload_video` | Upload an MP4 |
| `GET /feed` | Get ranked projects not yet swiped on |
| `POST /swipe` | Like, skip, or apply to a project |
| `POST /match` | View an application match as applicant or maintainer |
