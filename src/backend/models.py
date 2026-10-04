from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .database import Base


class Developer(Base):
    __tablename__ = "developers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    login: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    skills: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    repo_url: Mapped[str] = mapped_column(String, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String, nullable=True)
    needs: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    maintainer_id: Mapped[int] = mapped_column(ForeignKey("developers.id"), nullable=False, index=True)


class Swipe(Base):
    __tablename__ = "swipes"
    __table_args__ = (UniqueConstraint("developer_id", "project_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    developer_id: Mapped[int] = mapped_column(ForeignKey("developers.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)


class ApplicationReview(Base):
    __tablename__ = "application_reviews"

    swipe_id: Mapped[int] = mapped_column(ForeignKey("swipes.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("developers.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
