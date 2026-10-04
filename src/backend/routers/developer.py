from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_developer
from ..database import get_db
from ..models import ApplicationReview, Developer, Project, Swipe
from ..schemas import ApplicationRead, ApplicationStatus, DeveloperRead, DeveloperUpdate, ProjectRead

router = APIRouter(tags=["developers"])


@router.get("/me", response_model=DeveloperRead)
def get_me(me: Developer = Depends(current_developer)):
    return me


@router.put("/me", response_model=DeveloperRead)
def update_me(payload: DeveloperUpdate, me: Developer = Depends(current_developer),
              database: Session = Depends(get_db)):
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(me, field, value)
    database.commit()
    database.refresh(me)
    return me


@router.get("/me/projects", response_model=list[ProjectRead])
def my_projects(me: Developer = Depends(current_developer), database: Session = Depends(get_db)):
    return list(database.scalars(select(Project).where(Project.maintainer_id == me.id).order_by(Project.id)))


def _application_read(swipe: Swipe, developer: Developer, project: Project,
                      review: ApplicationReview | None) -> ApplicationRead:
    return ApplicationRead(
        application_id=swipe.id,
        status=ApplicationStatus(review.status) if review else ApplicationStatus.PENDING,
        developer=DeveloperRead.model_validate(developer),
        project=ProjectRead.model_validate(project),
    )


@router.get("/me/applications", response_model=list[ApplicationRead])
def my_applications(me: Developer = Depends(current_developer), database: Session = Depends(get_db)):
    rows = database.execute(
        select(Swipe, Developer, Project, ApplicationReview)
        .join(Developer, Developer.id == Swipe.developer_id)
        .join(Project, Project.id == Swipe.project_id)
        .outerjoin(ApplicationReview, ApplicationReview.swipe_id == Swipe.id)
        .where(Swipe.developer_id == me.id, Swipe.action == "APPLY")
        .order_by(Swipe.id.desc())
    )
    return [_application_read(*row) for row in rows]


@router.get("/me/incoming-applications", response_model=list[ApplicationRead])
def incoming_applications(me: Developer = Depends(current_developer),
                          database: Session = Depends(get_db)):
    rows = database.execute(
        select(Swipe, Developer, Project, ApplicationReview)
        .join(Developer, Developer.id == Swipe.developer_id)
        .join(Project, Project.id == Swipe.project_id)
        .outerjoin(ApplicationReview, ApplicationReview.swipe_id == Swipe.id)
        .where(Project.maintainer_id == me.id, Swipe.action == "APPLY")
        .order_by(Swipe.id.desc())
    )
    return [_application_read(*row) for row in rows]


@router.get("/developer/{developer_id}", response_model=DeveloperRead)
def get_developer(developer_id: int, _: Developer = Depends(current_developer),
                  database: Session = Depends(get_db)):
    developer = database.get(Developer, developer_id)
    if developer is None:
        raise HTTPException(404, "Developer not found")
    return developer
