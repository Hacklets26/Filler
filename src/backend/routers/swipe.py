from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Developer, Project, Swipe
from ..schemas import MatchRead, MatchRequest, SwipeCreate, SwipeRead


router = APIRouter(tags=["swipes"])


@router.post("/swipe", response_model=SwipeRead, status_code=status.HTTP_201_CREATED)
def create_swipe(payload: SwipeCreate, database: Session = Depends(get_db)):
    developer = database.get(Developer, payload.developer_id)
    if developer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Developer not found")
    if database.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing = database.scalar(
        select(Swipe).where(
            Swipe.developer_id == payload.developer_id,
            Swipe.project_id == payload.project_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A swipe for this project has already been recorded",
        )

    swipe = Swipe(
        developer_id=payload.developer_id,
        project_id=payload.project_id,
        action=payload.action.value,
    )
    developer.swipe_history = list(developer.swipe_history or []) + [payload.project_id]
    database.add(swipe)
    database.commit()
    database.refresh(swipe)
    return swipe


@router.post("/match", response_model=MatchRead)
def get_match(payload: MatchRequest, database: Session = Depends(get_db)):
    developer = database.get(Developer, payload.developer_id)
    if developer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Developer not found")
    project = database.get(Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    applied = database.scalar(
        select(Swipe.id).where(
            Swipe.developer_id == payload.developer_id,
            Swipe.project_id == payload.project_id,
            Swipe.action == "APPLY",
        )
    )
    if applied is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A match is available only after an APPLY swipe",
        )
    return MatchRead(developer=developer, project=project)