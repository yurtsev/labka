from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from src.core.db.enums import ScaleType

type CourseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type OptionalText = Annotated[str, StringConstraints(strip_whitespace=True)] | None


class RangeScaleSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[ScaleType.RANGE]
    min: int
    max: int

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.min >= self.max:
            raise ValueError("min должен быть меньше max")
        return self


class BinaryScaleSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[ScaleType.BINARY]


type ScaleSchema = Annotated[RangeScaleSchema | BinaryScaleSchema, Field(discriminator="type")]


class CourseUpdateRequest(BaseModel):
    name: CourseName
    description: OptionalText = None
    scale: ScaleSchema
    grading_note: OptionalText = None


class CourseCreateRequest(CourseUpdateRequest):
    group_ids: list[UUID] = Field(min_length=1)


class CourseGroupAddRequest(BaseModel):
    group_id: UUID


class GroupResponse(BaseModel):
    id: UUID
    name: str


class TeacherResponse(BaseModel):
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None


class ScaleResponse(BaseModel):
    type: ScaleType
    min: int | None
    max: int | None


class CourseResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    teacher: TeacherResponse
    scale: ScaleResponse
    grading_note: str | None
    is_archived: bool
    groups: list[GroupResponse]


class CoursePreviewResponse(BaseModel):
    id: UUID
    name: str
    teacher: TeacherResponse
    is_archived: bool
    groups: list[GroupResponse]
    pending_reviews: int | None


type GroupNameQuery = Annotated[str | None, Query(max_length=64)]
type AdmissionYearQuery = Annotated[int | None, Query(ge=1900, le=2999)]
