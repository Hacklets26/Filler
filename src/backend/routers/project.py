from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..auth import current_developer
from ..config import MAX_VIDEO_BYTES
from ..database import get_db
from ..models import ApplicationReview, Developer, Project, Swipe
from ..repos import inspect_repo
from ..schemas import ProjectCreate, ProjectRead, ProjectUpdate, RepoInspect, VideoUploadRead
from ..storage import VIDEO_DIRECTORY, delete_video_file

router = APIRouter(tags=["projects"])


def _owned(database: Session, project_id: int, me: Developer) -> Project:
    project = database.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.maintainer_id != me.id:
        raise HTTPException(403, "Only the maintainer can change this project")
    return project


@router.get("/repo/inspect", response_model=RepoInspect)
def repo_inspect(url: str, _: Developer = Depends(current_developer)):
    """Look up a GitHub/GitLab repo so the pitch form can prefill title, needs and tags."""
    try:
        return inspect_repo(url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/project", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, me: Developer = Depends(current_developer),
                   database: Session = Depends(get_db)):
    inspect_repo(payload.repo_url)  # 404 if the repo doesn't exist or isn't public
    project = Project(**payload.model_dump(), maintainer_id=me.id)
    database.add(project)
    database.commit()
    database.refresh(project)
    return project


@router.put("/project/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, me: Developer = Depends(current_developer),
                   database: Session = Depends(get_db)):
    project = _owned(database, project_id, me)
    changes = payload.model_dump(exclude_unset=True)
    previous_video_url = project.video_url
    if "repo_url" in changes and changes["repo_url"] != project.repo_url:
        inspect_repo(changes["repo_url"])
    for field, value in changes.items():
        if value is None and field not in ("video_url", "description"):
            continue
        setattr(project, field, value)
    database.commit()
    database.refresh(project)
    if project.video_url != previous_video_url:
        delete_video_file(previous_video_url)
    return project


@router.delete("/project/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, me: Developer = Depends(current_developer),
                   database: Session = Depends(get_db)):
    project = _owned(database, project_id, me)
    delete_video_file(project.video_url)
    database.execute(
        delete(ApplicationReview).where(
            ApplicationReview.swipe_id.in_(
                select(Swipe.id).where(Swipe.project_id == project.id)
            )
        )
    )
    database.execute(delete(Swipe).where(Swipe.project_id == project.id))
    database.delete(project)
    database.commit()


@router.get("/project/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, database: Session = Depends(get_db)):
    project = database.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(database: Session = Depends(get_db)):
    return list(database.scalars(select(Project).order_by(Project.id)).all())


@router.post("/upload_video", response_model=VideoUploadRead)
async def upload_video(request: Request, file: UploadFile = File(...),
                       _: Developer = Depends(current_developer)):
    if Path(Path(file.filename or "").name).suffix.lower() != ".mp4":
        raise HTTPException(415, "Only MP4 video uploads are supported")

    stored = f"{uuid4().hex}.mp4"
    destination = VIDEO_DIRECTORY / stored
    written = 0
    try:
        with destination.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_VIDEO_BYTES:
                    raise HTTPException(413, "Video must be 50 MB or smaller")
                out.write(chunk)
    except (OSError, HTTPException) as exc:
        destination.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(500, "Unable to save uploaded video") from exc
    finally:
        await file.close()
    return VideoUploadRead(video_url=str(request.base_url).rstrip("/") + f"/videos/{stored}")
