"""Explainable Patchwork project ranking.

The score combines only signals that are present for both sides of a match:

* skill fit (60%): requirement-level-weighted proficiency, capped at 100%;
* interest fit (25%): project tags that match a developer's interests;
* text fit (15%): developer skill/interest terms found in the project title or
  description.

Unavailable signals are left out and the remaining weights are renormalized.
That way a project without tags is not penalized for missing metadata, while
missing developer skills still count as zero proficiency for stated needs.
With no comparable signals at all, the score is neutral (50%). Exact ties are
broken by project ID in the feed endpoint.
"""

import re
from typing import TypedDict

from .models import Developer, Project

WEIGHTS = {"skill_fit": 0.60, "interest_fit": 0.25, "text_fit": 0.15}
STOP_WORDS = {
    "about", "after", "all", "and", "are", "build", "building", "for", "from",
    "have", "into", "its", "our", "project", "that", "the", "their", "this",
    "with", "your",
}
WORD_PATTERN = re.compile(r"[\w+#.-]+", re.UNICODE)


class MatchBreakdown(TypedDict):
    match_score: float
    skill_fit: float | None
    interest_fit: float | None
    text_fit: float | None


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in WORD_PATTERN.findall(value.casefold())
        if token not in STOP_WORDS and (len(token) > 1 or token in {"c", "r"})
    }


def explain_match(developer: Developer, project: Project) -> MatchBreakdown:
    """Return a 0..1 score and its measurable, independently inspectable parts."""
    scores: dict[str, float | None] = {
        "skill_fit": None,
        "interest_fit": None,
        "text_fit": None,
    }
    profile_skills = {
        _normalize(name): max(float(level), 0.0)
        for name, level in (developer.skills or {}).items()
    }
    needs = {
        _normalize(name): max(float(level), 0.0)
        for name, level in (project.needs or {}).items()
    }

    if needs:
        total_weight = sum(max(level, 1.0) for level in needs.values())
        scores["skill_fit"] = sum(
            max(level, 1.0) * min(profile_skills.get(name, 0.0) / max(level, 1.0), 1.0)
            for name, level in needs.items()
        ) / total_weight

    tags = {_normalize(tag) for tag in (project.tags or []) if _normalize(tag)}
    interests = {
        _normalize(interest)
        for interest in (developer.interests or [])
        if _normalize(interest)
    }
    if tags:
        scores["interest_fit"] = len(tags & interests) / len(tags)

    profile_terms: set[str] = set()
    for skill in profile_skills:
        profile_terms.update(_tokens(skill))
    for interest in interests:
        profile_terms.update(_tokens(interest))
    project_text = " ".join(
        part for part in (project.title or "", project.description or "") if part
    )
    text_terms = _tokens(project_text)
    if profile_terms and text_terms:
        scores["text_fit"] = len(profile_terms & text_terms) / len(profile_terms)

    available = [
        (name, score)
        for name, score in scores.items()
        if score is not None
    ]
    if not available:
        match_score = 0.5
    else:
        weight_total = sum(WEIGHTS[name] for name, _ in available)
        match_score = sum(
            WEIGHTS[name] * score
            for name, score in available
            if score is not None
        ) / weight_total

    return MatchBreakdown(
        match_score=round(match_score, 4),
        skill_fit=round(scores["skill_fit"], 4) if scores["skill_fit"] is not None else None,
        interest_fit=round(scores["interest_fit"], 4) if scores["interest_fit"] is not None else None,
        text_fit=round(scores["text_fit"], 4) if scores["text_fit"] is not None else None,
    )
