from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_developer
from ..database import get_db
from ..matching import explain_match
from ..models import Developer, Project, Swipe
from ..schemas import FeedProject, ProjectRead

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=list[FeedProject])
def get_feed(me: Developer = Depends(current_developer), database: Session = Depends(get_db)):
    seen = set(database.scalars(select(Swipe.project_id).where(Swipe.developer_id == me.id)))
    ranked = [
        (p, explain_match(me, p)) for p in database.scalars(select(Project))
        if p.id not in seen and p.maintainer_id != me.id
    ]
    ranked.sort(key=lambda item: (-float(item[1]["match_score"]), item[0].id))
    return [
        FeedProject.model_validate({**ProjectRead.model_validate(p).model_dump(), **score})
        for p, score in ranked
    ]
