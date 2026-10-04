from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .repos import canonical_repo_url
from .storage import VIDEO_URL_RE


def _skills(value: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, level in value.items():
        name = key.strip().lower()
        if not name:
            continue
        if not 1 <= level <= 5:
            raise ValueError(f"Level for '{name}' must be between 1 and 5")
        out[name] = level
    return out


def _words(value: list[str]) -> list[str]:
    return list(dict.fromkeys(v.strip().lower() for v in value if v.strip()))


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DeveloperUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    skills: dict[str, float] | None = None
    interests: list[str] | None = None

    @field_validator("skills")
    @classmethod
    def _norm_skills(cls, v):
        return _skills(v) if v is not None else v

    @field_validator("interests")
    @classmethod
    def _norm_interests(cls, v):
        return _words(v) if v is not None else v


class DeveloperRead(ORMModel):
    id: int
    login: str
    name: str
    avatar_url: str | None
    skills: dict[str, float]
    interests: list[str]


class _ProjectFields(BaseModel):
    @field_validator("repo_url", check_fields=False)
    @classmethod
    def _repo(cls, v):
        if v is None:
            return v
        return canonical_repo_url(v)

    @field_validator("video_url", check_fields=False)
    @classmethod
    def _video(cls, v):
        if v is None:
            return v
        if not VIDEO_URL_RE.match(v):
            raise ValueError("video_url must be a link returned by /upload_video")
        return v

    @field_validator("needs", check_fields=False)
    @classmethod
    def _needs(cls, v):
        return _skills(v) if v is not None else v

    @field_validator("tags", check_fields=False)
    @classmethod
    def _tags(cls, v):
        return _words(v) if v is not None else v


class ProjectCreate(_ProjectFields):
    title: str = Field(min_length=1)
    description: str | None = None
    repo_url: str
    video_url: str | None = None
    needs: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ProjectUpdate(_ProjectFields):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    repo_url: str | None = None
    video_url: str | None = None
    needs: dict[str, float] | None = None
    tags: list[str] | None = None


class ProjectRead(ORMModel):
    id: int
    title: str
    description: str | None
    repo_url: str
    video_url: str | None
    needs: dict[str, float]
    tags: list[str]
    maintainer_id: int


class FeedProject(ProjectRead):
    match_score: float
    skill_fit: float | None
    interest_fit: float | None
    text_fit: float | None
    interest_relevance_fit: float | None


class RepoInspect(BaseModel):
    repo_url: str
    title: str
    description: str | None
    needs: dict[str, float]
    tags: list[str]
    stars: int


class SwipeAction(str, Enum):
    SKIP = "SKIP"
    APPLY = "APPLY"


class SwipeCreate(BaseModel):
    project_id: int
    action: SwipeAction


class SwipeRead(ORMModel):
    id: int
    developer_id: int
    project_id: int
    action: SwipeAction


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ApplicationDecisionStatus(str, Enum):
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ApplicationDecision(BaseModel):
    status: ApplicationDecisionStatus


class ApplicationRead(BaseModel):
    application_id: int
    status: ApplicationStatus
    developer: DeveloperRead
    project: ProjectRead


class MatchRequest(BaseModel):
    developer_id: int
    project_id: int


class MatchRead(BaseModel):
    developer: DeveloperRead
    project: ProjectRead


class VideoUploadRead(BaseModel):
    video_url: str
