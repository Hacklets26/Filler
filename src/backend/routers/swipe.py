from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import current_developer
from ..database import get_db
from ..models import Developer, Project, Swipe
from ..schemas import DeveloperRead, MatchRead, MatchRequest, ProjectRead, SwipeCreate, SwipeRead

router = APIRouter(tags=["swipes"])


@router.post("/swipe", response_model=SwipeRead, status_code=status.HTTP_201_CREATED)
def create_swipe(payload: SwipeCreate, me: Developer = Depends(current_developer),
                 database: Session = Depends(get_db)):
    project = database.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.maintainer_id == me.id:
        raise HTTPException(400, "You can't swipe on your own project")
    swipe = Swipe(developer_id=me.id, project_id=project.id, action=payload.action.value)
    database.add(swipe)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(409, "A swipe for this project has already been recorded")
    database.refresh(swipe)
    return swipe


@router.post("/match", response_model=MatchRead)
def get_match(payload: MatchRequest, me: Developer = Depends(current_developer),
              database: Session = Depends(get_db)):
    developer = database.get(Developer, payload.developer_id)
    project = database.get(Project, payload.project_id)
    if developer is None or project is None:
        raise HTTPException(404, "Developer or project not found")
    if me.id not in (developer.id, project.maintainer_id):
        raise HTTPException(403, "Only the applicant or the maintainer can view a match")
    applied = database.scalar(select(Swipe.id).where(
        Swipe.developer_id == developer.id, Swipe.project_id == project.id, Swipe.action == "APPLY"))
    if applied is None:
        raise HTTPException(409, "A match is available only after an APPLY swipe")
    return MatchRead(
        developer=DeveloperRead.model_validate(developer),
        project=ProjectRead.model_validate(project),
    )
