import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


BACKEND_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = BACKEND_DIRECTORY / "patchwork.db"
LEGACY_DATABASE_PATH = BACKEND_DIRECTORY / "FILLER.db"
if not DEFAULT_DATABASE_PATH.exists() and LEGACY_DATABASE_PATH.exists():
    DEFAULT_DATABASE_PATH = LEGACY_DATABASE_PATH
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
