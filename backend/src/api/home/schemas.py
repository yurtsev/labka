from datetime import date, datetime, time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, PlainSerializer

from src.core.db.enums import AssignmentType, DeadlineType, LessonType
from src.core.grading.enums import ProgressStatus
from src.core.utils.moscow_time import to_moscow

type DeadlineOut = Annotated[datetime, PlainSerializer(to_moscow, return_type=datetime)]


class CourseRefResponse(BaseModel):
    id: UUID
    name: str


class GroupRefResponse(BaseModel):
    id: UUID
    name: str


class TeacherResponse(BaseModel):
    id: UUID
    last_name: str
    first_name: str
    middle_name: str | None


class HomeDeadlineResponse(BaseModel):
    assignment_id: UUID
    title: str
    type: AssignmentType
    deadline_type: DeadlineType
    deadline_at: DeadlineOut
    course: CourseRefResponse
    teacher: TeacherResponse
    status: ProgressStatus


class HomeLessonResponse(BaseModel):
    day: date
    starts_at: time
    ends_at: time
    slot: int | None
    lesson_type: LessonType
    room: str | None
    is_extra: bool
    course: CourseRefResponse
    group: GroupRefResponse


class HomeCourseResponse(BaseModel):
    id: UUID
    name: str
    teacher: TeacherResponse
    groups: list[GroupRefResponse]
    not_submitted: int | None
    pending_reviews: int | None


class HomeResponse(BaseModel):
    # Только у студента; `null`, если сдавать нечего («Все работы сданы»).
    nearest_deadline: HomeDeadlineResponse | None
    upcoming_deadlines: list[HomeDeadlineResponse]
    # Только у преподавателя.
    pending_reviews: int | None
    upcoming_lessons: list[HomeLessonResponse]
    courses: list[HomeCourseResponse]
    # Всего неархивных курсов; на главной показаны первые.
    courses_total: int
