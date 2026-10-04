"""Match score: 75% skill fit + 25% interest fit. Every term is explainable in one sentence.

skill_fit    = mean over needed skills of min(your_level / needed_level, 1)  (1.0 if no needs)
interest_fit = shared tags / project tags                                    (0.0 if no tags)
"""
from .models import Developer, Project

SKILL_WEIGHT, INTEREST_WEIGHT = 0.75, 0.25


def explain_match(developer: Developer, project: Project) -> dict[str, float]:
    mine = {k.lower(): v for k, v in (developer.skills or {}).items()}
    needs = project.needs or {}
    if needs:
        skill_fit = sum(
            1.0 if need <= 0 else min(mine.get(k.lower(), 0) / need, 1.0) for k, need in needs.items()
        ) / len(needs)
    else:
        skill_fit = 1.0
    tags = {t.lower() for t in project.tags or []}
    interests = {i.lower() for i in developer.interests or []}
    interest_fit = len(tags & interests) / len(tags) if tags else 0.0
    score = SKILL_WEIGHT * skill_fit + INTEREST_WEIGHT * interest_fit
    return {
        "match_score": round(score, 4),
        "skill_fit": round(skill_fit, 4),
        "interest_fit": round(interest_fit, 4),
    }
