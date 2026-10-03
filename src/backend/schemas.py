from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DeveloperCreate(BaseModel):
    name: str = Field(min_length=1)
    skills: dict[str, float] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)
    swipe_history: list[int] = Field(default_factory=list)


class DeveloperUpdate(BaseModel):
    skills: dict[str, float] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)
    swipe_history: list[int] = Field(default_factory=list)


class DeveloperRead(ORMModel):
    id: int
    name: str
    skills: dict[str, float]
    interests: list[str]
    swipe_history: list[int]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1)
    repo_url: str = Field(min_length=1)
    video_url: str | None = None
    needs: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    maintainer_id: int


class ProjectRead(ORMModel):
    id: int
    title: str
    repo_url: str
    video_url: str | None
    needs: dict[str, float]
    tags: list[str]
    maintainer_id: int


class SwipeAction(str, Enum):
    LIKE = "LIKE"
    SKIP = "SKIP"
    APPLY = "APPLY"


class SwipeCreate(BaseModel):
    developer_id: int
    project_id: int
    action: SwipeAction


class SwipeRead(ORMModel):
    id: int
    developer_id: int
    project_id: int
    action: SwipeAction


class MatchRequest(BaseModel):
    developer_id: int
    project_id: int


class MatchRead(BaseModel):
    developer: DeveloperRead
    project: ProjectRead


class VideoUploadRead(BaseModel):
    video_url: str


class FeedProject(ProjectRead):
    match_score: float
