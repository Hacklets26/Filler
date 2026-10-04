# FILLER backend

FILLER is a FastAPI service for developer profiles, project pitches, swipes,
matching, personalized feeds, and MP4 video uploads.

## Requirements

- Python 3.10 or newer
- Dependencies from the repository-root `requirements.txt`

From the repository root, install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Start the server

Run the provided entry point from the repository root:

```bash
python src/backend/app.py
```

The server listens on `http://localhost:30007`. The launcher finds the backend
package relative to its own file, so the project layout (including
`src/backend/main.py`, the router modules, and the other backend modules) must be
available when starting it. Running an isolated copy of `app.py` without those
modules is not sufficient to start the API.

Alternatively, run Uvicorn directly from the repository root:

```bash
uvicorn src.backend.main:app --reload
```

Interactive API documentation is available at
[`http://localhost:30007/docs`](http://localhost:30007/docs); the OpenAPI schema
is at [`http://localhost:30007/openapi.json`](http://localhost:30007/openapi.json).

## Configuration and storage

- By default, SQLite data is stored in `src/backend/FILLER.db`.
- Set `DATABASE_URL` to use a different SQLAlchemy database URL. For example:

  ```bash
  # Linux/macOS
  export DATABASE_URL=sqlite:///./FILLER.db

  # PowerShell
  $env:DATABASE_URL = "sqlite:///./FILLER.db"
  ```

- Uploaded videos are stored in `src/backend/videos/` and served publicly under
  `/videos/{stored_filename}`. The upload response provides the full URL.
- CORS allows any origin, method, and header. Credentialed CORS requests are
  disabled.

## API

All request and response bodies are JSON unless noted otherwise. Replace
`localhost:30007` with the deployed service URL when calling a remote server.

### Developers

Create a profile:

```http
POST /developer
Content-Type: application/json
```

```json
{
  "name": "Ada",
  "skills": {"python": 3, "sql": 2},
  "interests": ["data", "open source"]
}
```

`skills`, `interests`, and `swipe_history` default to empty objects/lists.
Successful creation returns `201 Created` and includes the new `id`.

- `GET /developer/{developer_id}` retrieves a profile.
- `PUT /developer/{developer_id}` updates profile fields. Supply any fields to
  update; omitted fields retain their current values. For example:

  ```json
  {"skills": {"python": 4}, "interests": ["data"]}
  ```

### Projects

Create a pitch (the `maintainer_id` must be an existing developer):

```http
POST /project
Content-Type: application/json
```

```json
{
  "title": "Data Garden",
  "repo_url": "https://github.com/example/data-garden",
  "video_url": "http://localhost:30007/videos/your-upload.mp4",
  "needs": {"python": 3, "sql": 1},
  "tags": ["data", "open source"],
  "maintainer_id": 1
}
```

`video_url`, `needs`, and `tags` can be omitted; their defaults are `null`, an
empty object, and an empty list respectively.

- `GET /project/{project_id}` retrieves one project.
- `GET /projects` lists all projects.

### Upload a pitch video

Send a multipart form upload with the field name `file`. Only filenames ending
in `.mp4` are accepted.

```bash
curl -F "file=@pitch.mp4" http://localhost:30007/upload_video
```

The response contains a public `video_url`, for example:

```json
{"video_url": "http://localhost:30007/videos/2d9e...c31.mp4"}
```

Use that URL as `video_url` when creating the project. The video can then be
retrieved with `GET /videos/{stored_filename}`.

### Swipes and matches

Record a swipe:

```http
POST /swipe
Content-Type: application/json
```

```json
{"developer_id": 1, "project_id": 2, "action": "APPLY"}
```

`action` must be `LIKE`, `SKIP`, or `APPLY`. A developer can record only one
swipe per project; subsequent attempts return `409 Conflict`. Recording a swipe
also adds the project ID to that developer's `swipe_history`.

After an `APPLY`, retrieve the associated developer and project:

```http
POST /match
Content-Type: application/json
```

```json
{"developer_id": 1, "project_id": 2}
```

The endpoint returns both objects. It returns `409 Conflict` if no `APPLY` has
been recorded for that developer and project.

### Personalized feed

```http
GET /feed/{developer_id}
```

The response is a list of project objects, each with a `match_score` from `0`
to `1`, sorted from highest to lowest score. Projects in `swipe_history` are
excluded.

The score is calculated by averaging the skill contributions for the project's
requirements: a developer skill at or above the requested level contributes
`+1.0`, a positive skill below the requested level contributes `+0.5`, and a
missing skill contributes `-0.2`. This average is clamped to `[0, 1]`. If one
or more project tags match developer interests, `0.2` is added, with the final
score capped at `1`. A project with no skill requirements starts with a skill
score of `0`.

## Error responses

Typical errors include:

- `404 Not Found` when a developer, project, or maintainer does not exist.
- `409 Conflict` for duplicate swipes or for requesting a match without an
  `APPLY`.
- `415 Unsupported Media Type` when the uploaded filename is not an MP4.
- `422 Unprocessable Entity` for invalid request data.
