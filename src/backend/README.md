# Patchwork backend

Patchwork's FastAPI service handles GitHub OAuth, contributor profiles, project
pitches, recommendations, and application review.

## Deploy and run

The backend folder is a supported deployment root. Install from its dependency
manifest and launch it there:

```bash
python -m pip install -r requirements.txt
python app.py
```

The same launcher works from the repository root as `python src/backend/app.py`.
It loads the Python package relative to its own file.

For the public deployment, configure:

- `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` from the GitHub OAuth app.
- `PUBLIC_API_URL=https://backend.ifamished.com`.
- `FRONTEND_URL=https://patchwork.hacklets.dev`.
- A unique `JWT_SECRET` with at least 32 random characters.

Register `https://backend.ifamished.com/auth/github/callback` as the GitHub
OAuth callback URL. The service refuses to start an OAuth redirect when either
GitHub credential is missing.

The backend dependency manifest installs **PyJWT**, which provides the
`jwt.encode` and `jwt.decode` APIs used by login. The similarly named `jwt`
PyPI distribution is a different package and must not be installed in its
place.

## Persistence and application routes

When `DATABASE_URL` is not set, Python creates `patchwork.db` in the backend
directory using the SQLAlchemy models. Database files are ignored by Git.
Set `DATABASE_URL` to use another SQLAlchemy-supported database.

Applications are created from `APPLY` swipes with initial `pending` status.
`GET /me/applications` lists the signed-in contributor's applications;
`GET /me/incoming-applications` lists applications to their projects. A
maintainer can set status to `accepted` or `declined` with
`PUT /applications/{application_id}`. Only the project maintainer may review
an application. Older `APPLY` swipes without a review row appear as pending.

## Recommendation scoring

See [the root README's matching section](../../README.md#matching-and-recommendations)
for the complete formula, signal weights, missing-data handling, text matching,
and deterministic feed ordering.
