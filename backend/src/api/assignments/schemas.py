from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    model_validator,
)

from src.api.schemas import UploadedFileRequest
from src.core.db.enums import AssignmentType, DeadlineType, ScaleType
from src.core.grading.enums import ProgressStatus
from src.core.utils.moscow_time import assume_moscow, to_moscow

type Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type OptionalText = Annotated[str, StringConstraints(strip_whitespace=True)] | None
# Дедлайн вводится по МСК: время без часового пояса считается московским.
type DeadlineIn = Annotated[datetime, AfterValidator(assume_moscow)]
type DeadlineOut = Annotated[datetime, PlainSerializer(to_moscow, return_type=datetime)]


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


class AssignmentUpdateRequest(BaseModel):
    type: AssignmentType
    title: Title
    description: OptionalText = None
    deadline_type: DeadlineType
    deadline_at: DeadlineIn | None = None
    # Не задана — шкала курса.
    scale: ScaleSchema | None = None
    grading_note: OptionalText = None

    @model_validator(mode="after")
    def check_deadline(self) -> Self:
        if (self.deadline_type == DeadlineType.NONE) != (self.deadline_at is None):
            raise ValueError("дата дедлайна нужна для мягкого и жёсткого дедлайна и только для них")
        return self


class AssignmentCreateRequest(AssignmentUpdateRequest):
    files: list[UploadedFileRequest] = Field(default_factory=list)


class ScaleResponse(BaseModel):
    type: ScaleType
    min: int | None
    max: int | None


class GradeResponse(BaseModel):
    score: int | None
    passed: bool | None


class ProgressResponse(BaseModel):
    status: ProgressStatus
    grade: GradeResponse | None
    attempts: int
    last_submitted_at: datetime | None
    last_is_late: bool
    can_submit: bool = Field(
        description="Можно ли сейчас отправить попытку: те же правила, что при отправке"
    )


class SummaryResponse(BaseModel):
    students: int
    submitted: int
    on_review: int
    accepted: int


class AssignmentFileResponse(BaseModel):
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str


class AssignmentResponse(BaseModel):
    id: UUID
    course_id: UUID
    type: AssignmentType
    title: str
    description: str | None
    deadline_type: DeadlineType
    deadline_at: DeadlineOut | None
    scale: ScaleResponse
    has_own_scale: bool
    grading_note: str | None
    created_at: datetime
    updated_at: datetime
    files: list[AssignmentFileResponse]
    # У студента — его статус и оценка; у преподавателя — сводка и всего попыток.
    my_progress: ProgressResponse | None
    summary: SummaryResponse | None
    attempts_total: int | None


class StudentRowResponse(BaseModel):
    student_id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    group_id: UUID
    group_name: str
    progress: ProgressResponse
