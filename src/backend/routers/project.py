from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Developer, Project
from ..schemas import ProjectCreate, ProjectRead, VideoUploadRead
from ..storage import VIDEO_DIRECTORY


router = APIRouter(tags=["projects"])


@router.post(
    "/project",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(payload: ProjectCreate, database: Session = Depends(get_db)):
    if database.get(Developer, payload.maintainer_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintainer developer not found",
        )

    project = Project(**payload.model_dump())
    database.add(project)
    database.commit()
    database.refresh(project)
    return project


@router.get("/project/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, database: Session = Depends(get_db)):
    project = database.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(database: Session = Depends(get_db)):
    return list(database.scalars(select(Project).order_by(Project.id)).all())


@router.post("/upload_video", response_model=VideoUploadRead)
async def upload_video(request: Request, file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() != ".mp4":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only MP4 video uploads are supported",
        )

    stored_filename = f"{uuid4().hex}.mp4"
    destination = VIDEO_DIRECTORY / stored_filename
    try:
        with destination.open("wb") as video_file:
            while chunk := await file.read(1024 * 1024):
                video_file.write(chunk)
    except OSError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save uploaded video",
        ) from exc
    finally:
        await file.close()

    return VideoUploadRead(video_url=str(request.base_url).rstrip("/") + f"/videos/{stored_filename}")