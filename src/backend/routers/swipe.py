from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import current_developer
from ..database import get_db
from ..models import ApplicationReview, Developer, Project, Swipe
from ..schemas import (
    ApplicationDecision,
    ApplicationRead,
    ApplicationStatus,
    DeveloperRead,
    MatchRead,
    MatchRequest,
    ProjectRead,
    SwipeCreate,
    SwipeRead,
)

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
        if payload.action.value == "APPLY":
            database.flush()
            database.add(ApplicationReview(swipe_id=swipe.id))
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


@router.put("/applications/{application_id}", response_model=ApplicationRead)
def review_application(
    application_id: int,
    payload: ApplicationDecision,
    me: Developer = Depends(current_developer),
    database: Session = Depends(get_db),
):
    swipe = database.get(Swipe, application_id)
    if swipe is None or swipe.action != "APPLY":
        raise HTTPException(404, "Application not found")
    developer = database.get(Developer, swipe.developer_id)
    project = database.get(Project, swipe.project_id)
    if developer is None or project is None:
        raise HTTPException(404, "Application no longer exists")
    if project.maintainer_id != me.id:
        raise HTTPException(403, "Only the project maintainer can review applications")

    review = database.get(ApplicationReview, swipe.id)
    if review is None:
        review = ApplicationReview(swipe_id=swipe.id)
        database.add(review)
    review.status = payload.status.value
    review.reviewed_by = me.id
    review.reviewed_at = datetime.now(timezone.utc)
    database.commit()
    return ApplicationRead(
        application_id=swipe.id,
        status=ApplicationStatus(payload.status.value),
        developer=DeveloperRead.model_validate(developer),
        project=ProjectRead.model_validate(project),
    )
