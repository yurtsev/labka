from datetime import date, time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.core.db.enums import ExamType

type Room = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] | None


class ExamRequest(BaseModel):
    group_id: UUID
    exam_type: ExamType
    day: date
    slot: int = Field(ge=1, description="Номер пары из сетки `GET /api/schedule/slots`")
    room: Room = None


class GroupResponse(BaseModel):
    id: UUID
    name: str


class ExamResponse(BaseModel):
    id: UUID
    group: GroupResponse
    exam_type: ExamType
    day: date
    slot: int | None
    starts_at: time
    ends_at: time
    room: str | None


class ExamsResponse(BaseModel):
    items: list[ExamResponse]
