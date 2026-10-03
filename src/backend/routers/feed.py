from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..matching import calculate_match_score
from ..models import Developer, Project
from ..schemas import FeedProject, ProjectRead


router = APIRouter(tags=["feed"])


@router.get("/feed/{developer_id}", response_model=list[FeedProject])
def get_feed(developer_id: int, database: Session = Depends(get_db)):
    developer = database.get(Developer, developer_id)
    if developer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Developer not found")

    previously_swiped = set(developer.swipe_history or [])
    projects = database.scalars(select(Project)).all()
    ranked_projects = [
        (project, calculate_match_score(developer, project))
        for project in projects
        if project.id not in previously_swiped
    ]
    ranked_projects.sort(key=lambda item: (-item[1], item[0].id))

    return [
        FeedProject(**ProjectRead.model_validate(project).model_dump(), match_score=score)
        for project, score in ranked_projects
    ]