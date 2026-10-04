# Patchwork

Patchwork connects open-source maintainers with contributors who have the skills
and interests their projects need. Sign in with GitHub, discover ranked projects,
apply with one click, and review incoming applications from your own pitches.

## Run locally

```bash
python -m pip install -r requirements-dev.txt
cd src/frontend
npm install
```

Configure GitHub OAuth and local URLs in the backend environment:

```text
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
PUBLIC_API_URL=http://localhost:30007
FRONTEND_URL=http://localhost:5173
JWT_SECRET=<a unique random value of at least 32 characters>
```

Run the API from the repository root with `python src/backend/app.py`, then run
the frontend from `src/frontend` with `npm run dev`. The default API docs are at
`http://localhost:30007/docs`.

For production, the frontend targets `https://backend.ifamished.com` and is
published at `https://patchwork.millered001.workers.dev`. Set the GitHub OAuth
callback URL to `https://backend.ifamished.com/auth/github/callback`, and
configure `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `JWT_SECRET` in the
backend deployment. Production builds deliberately ignore `VITE_API_BASE`;
local development may use it to override the local API address.

The backend creates `src/backend/patchwork.db` in Python from the SQLAlchemy
models. Database files are ignored by Git. Run backend tests from the root with
`python -m pytest tests`.

## Matching and recommendations

Patchwork computes a transparent score from 0 to 1 for each unseen project.
Scores are rounded to four decimal places for display and stable sorting.

### Signals

**Skill fit (60% of available weight)** measures proficiency against stated
requirements. For every required skill `s`, the contributor's level `u_s`
contributes `min(u_s / max(r_s, 1), 1)`, where `r_s` is the project's requested
level. Each requirement is weighted by `max(r_s, 1)`, so a stronger stated need
matters proportionally more:

```text
skill_fit = sum(max(r_s, 1) * min(u_s / max(r_s, 1), 1))
            / sum(max(r_s, 1))
```

An absent skill has level zero. Names are compared case-insensitively after
trimming whitespace. When the project states no skills, skill fit is
unavailable—not a perfect match.

**Interest fit (25% of available weight)** is the fraction of project tags that
appear in the contributor's interests:

```text
interest_fit = count(project tags ∩ contributor interests) / count(project tags)
```

Tags and interests are compared case-insensitively after trimming. If a project
has no tags, this signal is unavailable.

**Text fit (15% of available weight)** measures whether terms from the
contributor's skill and interest profile appear in the project's title or
description:

```text
text_fit = count(profile terms ∩ project title/description terms)
           / count(profile terms)
```

Text tokenization is case-insensitive, ignores a small set of generic words,
and keeps technical tokens such as `C++`, `C#`, and `R`. If either side has no
usable terms, text fit is unavailable.

### Combining signals and ordering the feed

The final score is the weighted mean of available signals only; their weights
are renormalized to sum to one. For example, if skill fit and interest fit are
available but title/description text is not, the weights become `60/85` and
`25/85`. Missing project metadata is therefore not treated as a mismatch. If
none of the three signals can be compared, the project receives a neutral
`0.5` score.

The feed excludes the signed-in contributor's own projects and any project on
which they already swiped. It sorts by descending score and then ascending
project ID, so ties are deterministic. The UI lets contributors search project
names, descriptions, tags, and required skills; filter by minimum score; and
sort alphabetically or by match score. Refresh reloads recommendations without
resetting the current filters. Score breakdown bars display only the signals
that were actually available.

The interface includes light and dark themes. The theme switch is available
from the sign-in screen and the main navigation, follows the device preference
on first visit, and remembers the user's selection in local browser storage.
Motion respects the operating system's reduced-motion preference.

## Applications

Applying creates a pending application. Contributors can track applications in
**Applications**; maintainers see incoming applicants there and can accept or
decline. Only a project's maintainer can change an application's status. Pass
records a skip and removes the project from the feed. There is no like action.

## Video pitches

Public GitHub/GitLab repository links can prefill pitch details. Optional videos
must be MP4 and no larger than 50 MB.
