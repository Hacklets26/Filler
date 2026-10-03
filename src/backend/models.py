from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .database import Base


class Developer(Base):
    __tablename__ = "developers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    skills: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    swipe_history: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    repo_url: Mapped[str] = mapped_column(String, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String, nullable=True)
    needs: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    maintainer_id: Mapped[int] = mapped_column(
        ForeignKey("developers.id"), nullable=False, index=True
    )


class Swipe(Base):
    __tablename__ = "swipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    developer_id: Mapped[int] = mapped_column(
        ForeignKey("developers.id"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)