from .models import Developer, Project


def calculate_match_score(developer: Developer, project: Project) -> float:
    """Return the normalized skill score with an optional interest bonus."""
    requirements = project.needs or {}
    if requirements:
        score = 0.0
        for skill, required_level in requirements.items():
            developer_level = (developer.skills or {}).get(skill)
            if developer_level is None:
                score -= 0.2
            elif developer_level >= required_level:
                score += 1.0
            elif developer_level > 0:
                score += 0.5

        skill_score = max(0.0, min(1.0, score / len(requirements)))
    else:
        skill_score = 0.0

    has_interest_overlap = bool(set(project.tags or []).intersection(developer.interests or []))
    return round(min(1.0, skill_score + (0.2 if has_interest_overlap else 0.0)), 4)
