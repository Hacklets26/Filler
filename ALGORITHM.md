# Project matching and recommendations

Patchwork ranks projects for a developer using three measurable signals: how
well the developer's skills meet the project's stated needs, how well project
tags match the developer's interests, and whether the developer's skills or
interests appear in the project's title or description. Each signal is
calculated independently and the available signals are combined into a
0-to-1 match score.

The implementation is in [`src/backend/matching.py`](src/backend/matching.py).
The feed endpoint applies that scorer in
[`src/backend/routers/feed.py`](src/backend/routers/feed.py).

## Inputs

The scorer reads these fields:

| Source | Fields used |
| --- | --- |
| Developer profile | `skills` (skill name and numeric proficiency), `interests` |
| Project | `needs` (skill name and numeric required level), `tags`, `title`, `description` |

Skill and interest names are stripped of surrounding whitespace and compared
without regard to case. Skill names otherwise need to match exactly: the
scorer does not infer that synonyms or related technologies are equivalent.

Project needs and developer skills are numeric levels. The current skill picker
stores Beginner, Intermediate, Advanced, and Expert as levels 1 through 4;
the API also accepts values through level 5, and repository inspection can
suggest levels based on language usage. The scorer uses the stored numeric
values directly rather than interpreting their display labels.

## Individual signals

Every signal is between 0 and 1. A value of 1 means a full match for that
signal and 0 means no match for it. A signal can be unavailable (`null`) when
there is not enough corresponding project data to calculate it.

### Skill fit (60% of the available weight)

Skill fit is a requirement-level-weighted average. For each project need:

1. Look up the developer's proficiency for the same normalized skill name.
   A skill missing from the developer's profile has proficiency zero.
2. Divide the developer's proficiency by the required level, capping the
   result at 1.
3. Weight that result by the required level (with a minimum weight of 1).

In formula form, for each need `s`, let `r_s = max(required level, 1)` and
`p_s` be the developer's proficiency, or zero if they have not listed that
skill:

```text
skill_fit = sum(r_s * min(p_s / r_s, 1)) / sum(r_s)
```

Consequently, meeting or exceeding a requirement earns full credit for it,
partial proficiency earns proportional credit, and extra proficiency does not
add more than full credit. More demanding needs have more influence on the
skill-fit average. If the project lists no needs, skill fit is unavailable.
If it does list needs but the developer has no skills, skill fit is zero, not
unavailable.

### Interest fit (25% of the available weight)

Project tags and developer interests are each normalized and treated as sets.
The score is the fraction of the project's distinct, non-empty tags also
listed as developer interests:

```text
interest_fit = count(project tags also in developer interests)
               / count(distinct project tags)
```

An interest that has no corresponding project tag does not add credit. If
there are no project tags, interest fit is unavailable. If there are tags but
the developer has no matching interests, interest fit is zero.

### Text fit (15% of the available weight)

Text fit measures how well the developer's distinct skill and interest phrases
are represented in the project's title or description. It is a literal,
case-insensitive text comparison, not semantic search.

1. Treat each skill name and interest as a separate profile concept; duplicate
   phrases are counted once.
2. Tokenize profile phrases, title, and description case-insensitively using
   `[\w]+(?:[+#]+)?`. Punctuation such as spaces, hyphens, and periods
   separates tokens, so `Machine-Learning` and `machine learning` produce the
   same phrase tokens. One-character tokens are ignored except for `c` and
   `r`.
3. First look for the entire profile phrase as a consecutive sequence of
   tokens in either the title or description. A full phrase match earns full
   credit for that concept. This exact-phrase check happens before stop words
   are ignored.
4. If the full phrase is not present, calculate partial credit from the
   fraction of that concept's non-stop-word tokens found anywhere in the
   title or description. Stop words are `about`, `after`, `all`, `and`, `are`,
   `build`, `building`, `for`, `from`, `have`, `into`, `its`, `our`,
   `project`, `that`, `the`, `their`, `this`, `with`, and `your`.
5. Average the credit across the distinct profile concepts:

```text
text_fit = sum(credit for each profile concept) / count(profile concepts)
```

For example, a developer with the skill `Machine Learning` gets full credit
for that skill when a project title contains `Machine-Learning`, despite the
hyphen. If the same developer also has the interest `Build`, the title
`Machine-Learning Build` matches both concepts; `Build` is still recognized
because exact phrase matches are checked before stop words are excluded from
partial matches.

Title and description are both searched; repeated words do not add extra
credit. If the profile has no skill or interest phrases, or the project has
neither a title nor a description, text fit is unavailable. If project text is
present but none of the concepts match, the score is zero.

## Combining the signals

The overall match keeps three scoring signals at these weights:

| Signal | Weight |
| --- | ---: |
| Skill fit | 60% |
| Interest fit | 25% |
| Text fit | 15% |

Only available signals contribute. Their weights are renormalized by dividing
by the sum of the available weights:

```text
match_score = sum(weight_i * score_i for each available signal i)
              / sum(weight_i for each available signal i)
```

The feed's component bars show Skill fit separately and combine Interest fit
with Text fit in a single **Interest & relevance** bar. This display value is
a weighted average using the original `0.25` and `0.15` weights, renormalized
over whichever of those two component scores are available:

```text
interest_relevance_fit =
    sum(weight_i * score_i for available interest/text signals i)
    / sum(weight_i for available interest/text signals i)
```

Thus the combined bar is the Interest fit when text fit is unavailable, the
Text fit when interest fit is unavailable, and unavailable if neither can be
calculated. It does not alter the three underlying scores or their
contribution to the overall match.

For example, if a project has skill fit `0.5`, interest fit `0.5`, and text
fit `2/3`, all three overall-match signals are available:

```text
(0.60 * 0.5 + 0.25 * 0.5 + 0.15 * 2/3) / (0.60 + 0.25 + 0.15)
= 0.525
```

If text fit is unavailable, the denominator becomes `0.60 + 0.25`, so the
remaining skill and interest signals still account for the full score. If
none of the three signals is available, the score is a neutral `0.5`.

The returned overall score and available component scores are rounded to four
decimal places. The feed displays the overall score as a rounded percentage
and shows component percentages for skill fit and combined interest and
relevance.

## Feed selection and ordering

For a feed request, the backend:

1. Excludes projects maintained by the requesting developer.
2. Excludes projects the developer has already swiped on, whether they passed
   or showed interest.
3. Calculates a match breakdown for each remaining project.
4. Sorts by match score, highest first; ties are ordered by ascending project
   ID for a stable result.

The feed response includes the project data, overall score, and individual
signal scores. The frontend can further filter by minimum match and text
search (project title, description, repository URL, tags, and needed skill
names), or choose alphabetical sorting. These display filters do not change
the backend match score.

## Repository-based project suggestions

When a maintainer inspects a GitHub or GitLab repository, the backend can
pre-fill project needs from its detected programming-language shares. It
considers at most the five most-used languages, keeps languages with at least
5% of the total, and suggests a need level of:

| Language share | Suggested level |
| --- | ---: |
| 50% or more | 4 |
| 20% to less than 50% | 3 |
| 5% to less than 20% | 2 |
| Less than 5% | Not included |

Repository topics can also be suggested as tags (up to eight). These are
initial suggestions for the project form; the project needs and tags saved
with the project are what the matching algorithm uses. Repository stars and
other repository metadata do not directly affect the match score.

## What the algorithm does not consider

The score does not directly use project popularity, stars, recency, repository
activity, maintainer identity, application history beyond excluding swiped
projects, or semantic similarity between different skill names and phrases.
It is a transparent ranking aid based on the explicit profile and project
metadata, not a prediction of project quality or likelihood of acceptance.
