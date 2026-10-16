from datetime import date, datetime, time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from src.api.calendar.enums import CalendarItemKind
from src.core.db.enums import AssignmentType, DeadlineType, ExamType, LessonType, SemesterTerm
from src.core.grading.enums import ProgressStatus
from src.core.schedule.enums import CalendarView


class CourseRefResponse(BaseModel):
    id: UUID
    name: str


class GroupRefResponse(BaseModel):
    id: UUID
    name: str


class CalendarLessonResponse(BaseModel):
    course: CourseRefResponse
    group: GroupRefResponse
    lesson_type: LessonType
    slot: int | None
    room: str | None
    is_extra: bool


class CalendarExamResponse(BaseModel):
    course: CourseRefResponse
    group: GroupRefResponse
    exam_type: ExamType
    slot: int | None
    room: str | None


class CalendarDeadlineResponse(BaseModel):
    assignment_id: UUID
    title: str
    type: AssignmentType
    deadline_type: DeadlineType
    course: CourseRefResponse
    my_status: ProgressStatus | None


class CalendarTaskResponse(BaseModel):
    id: UUID
    title: str
    is_done: bool


class CalendarItemResponse(BaseModel):
    kind: CalendarItemKind
    day: date
    starts_at: time | None
    ends_at: time | None
    lesson: CalendarLessonResponse | None
    exam: CalendarExamResponse | None
    deadline: CalendarDeadlineResponse | None
    task: CalendarTaskResponse | None


class PeriodResponse(BaseModel):
    view: CalendarView
    starts_on: date
    ends_on: date
    prev: date
    next: date


class WeekResponse(BaseModel):
    starts_on: date
    ends_on: date
    term: SemesterTerm | None
    number: int | None
    is_even: bool | None


class CalendarResponse(BaseModel):
    period: PeriodResponse
    weeks: list[WeekResponse]
    items: list[CalendarItemResponse]


class TaskRequest(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    due_date: date
    due_time: time | None = None


class TaskDoneRequest(BaseModel):
    is_done: bool


class TaskResponse(BaseModel):
    id: UUID
    title: str
    due_date: date
    due_time: time | None
    is_done: bool
    created_at: datetime


class TasksResponse(BaseModel):
    items: list[TaskResponse]
