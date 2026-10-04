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
WORD_PATTERN = re.compile(r"[\w]+(?:[+#]+)?", re.UNICODE)


class MatchBreakdown(TypedDict):
    match_score: float
    skill_fit: float | None
    interest_fit: float | None
    text_fit: float | None
    interest_relevance_fit: float | None


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in WORD_PATTERN.findall(value.casefold())
        if len(token) > 1 or token in {"c", "r"}
    )


def _contains_phrase(text: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    return any(
        text[index:index + len(phrase)] == phrase
        for index in range(len(text) - len(phrase) + 1)
    )


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

    profile_concepts = {
        tokens
        for value in (*profile_skills, *interests)
        if (tokens := _tokens(value))
    }
    title_tokens = _tokens(project.title or "")
    description_tokens = _tokens(project.description or "")
    project_terms = {
        token
        for token in (*title_tokens, *description_tokens)
        if token not in STOP_WORDS
    }
    if profile_concepts and (title_tokens or description_tokens):
        concept_scores = []
        for concept in profile_concepts:
            if _contains_phrase(title_tokens, concept) or _contains_phrase(description_tokens, concept):
                concept_scores.append(1.0)
                continue
            useful_terms = set(concept) - STOP_WORDS
            concept_scores.append(
                len(useful_terms & project_terms) / len(useful_terms)
                if useful_terms else 0.0
            )
        scores["text_fit"] = sum(concept_scores) / len(concept_scores)

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

    interest_relevance_signals = [
        (name, scores[name])
        for name in ("interest_fit", "text_fit")
        if scores[name] is not None
    ]
    if interest_relevance_signals:
        combined_weight = sum(WEIGHTS[name] for name, _ in interest_relevance_signals)
        interest_relevance_fit = sum(
            WEIGHTS[name] * score
            for name, score in interest_relevance_signals
            if score is not None
        ) / combined_weight
    else:
        interest_relevance_fit = None

    return MatchBreakdown(
        match_score=round(match_score, 4),
        skill_fit=round(scores["skill_fit"], 4) if scores["skill_fit"] is not None else None,
        interest_fit=round(scores["interest_fit"], 4) if scores["interest_fit"] is not None else None,
        text_fit=round(scores["text_fit"], 4) if scores["text_fit"] is not None else None,
        interest_relevance_fit=(
            round(interest_relevance_fit, 4) if interest_relevance_fit is not None else None
        ),
    )
