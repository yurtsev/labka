from datetime import date, time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from src.api.schemas import SemesterResponse
from src.core.db.enums import LessonType, ScheduleRepeat

type Room = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] | None


class RuleRequest(BaseModel):
    group_id: UUID
    lesson_type: LessonType
    weekday: int = Field(ge=1, le=7, description="День недели, 1 — понедельник")
    slot: int = Field(ge=1, description="Номер пары из сетки `GET /api/schedule/slots`")
    repeat: ScheduleRepeat
    room: Room = None


class ExtraRequest(BaseModel):
    group_id: UUID
    lesson_type: LessonType
    day: date
    slot: int = Field(ge=1, description="Номер пары из сетки `GET /api/schedule/slots`")
    room: Room = None


class GroupResponse(BaseModel):
    id: UUID
    name: str


class RuleResponse(BaseModel):
    id: UUID
    group: GroupResponse
    lesson_type: LessonType
    weekday: int
    slot: int | None
    starts_at: time
    ends_at: time
    repeat: ScheduleRepeat
    room: str | None


class ExtraResponse(BaseModel):
    id: UUID
    group: GroupResponse
    lesson_type: LessonType
    day: date
    slot: int | None
    starts_at: time
    ends_at: time
    room: str | None


class CourseScheduleResponse(BaseModel):
    semester: SemesterResponse
    rules: list[RuleResponse]
    extras: list[ExtraResponse]


class SlotResponse(BaseModel):
    number: int
    starts_at: time
    ends_at: time


class SlotsResponse(BaseModel):
    items: list[SlotResponse]
