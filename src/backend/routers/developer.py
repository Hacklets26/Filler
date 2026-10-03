from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Developer
from ..schemas import DeveloperCreate, DeveloperRead, DeveloperUpdate


router = APIRouter(tags=["developers"])


@router.post(
    "/developer",
    response_model=DeveloperRead,
    status_code=status.HTTP_201_CREATED,
)
def create_developer(payload: DeveloperCreate, database: Session = Depends(get_db)):
    developer = Developer(**payload.model_dump())
    database.add(developer)
    database.commit()
    database.refresh(developer)
    return developer


@router.get("/developer/{developer_id}", response_model=DeveloperRead)
def get_developer(developer_id: int, database: Session = Depends(get_db)):
    developer = database.get(Developer, developer_id)
    if developer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Developer not found")
    return developer


@router.put("/developer/{developer_id}", response_model=DeveloperRead)
def update_developer(
    developer_id: int,
    payload: DeveloperUpdate,
    database: Session = Depends(get_db),
):
    developer = database.get(Developer, developer_id)
    if developer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Developer not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(developer, field, value)

    database.commit()
    database.refresh(developer)
    return developer