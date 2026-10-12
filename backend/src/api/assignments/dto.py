from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.core.db.enums import AssignmentType, DeadlineType
from src.core.grading.dto import Progress, Scale, Summary
from src.core.grading.enums import ProgressStatus


@dataclass(frozen=True)
class AssignmentFields:
    """Редактируемые поля задания; `scale=None` — шкала курса."""

    type: AssignmentType
    title: str
    description: str | None
    deadline_type: DeadlineType
    deadline_at: datetime | None
    scale: Scale | None
    grading_note: str | None


@dataclass(frozen=True)
class UploadedFile:
    """Файл, который браузер уже загрузил в S3 по форме бэкенда."""

    key: str
    file_name: str


@dataclass(frozen=True)
class AssignmentFile:
    id: UUID
    file_name: str
    file_size: int
    content_type: str
    download_url: str


@dataclass(frozen=True)
class Assignment:
    """Карточка задания: у студента — его положение, у преподавателя — сводка."""

    id: UUID
    course_id: UUID
    type: AssignmentType
    title: str
    description: str | None
    deadline_type: DeadlineType
    deadline_at: datetime | None
    scale: Scale
    has_own_scale: bool
    grading_note: str | None
    created_at: datetime
    updated_at: datetime
    files: tuple[AssignmentFile, ...]
    my_progress: Progress | None
    summary: Summary | None
    attempts_total: int | None


@dataclass(frozen=True)
class StudentRowsFilter:
    group_id: UUID | None
    status: ProgressStatus | None


@dataclass(frozen=True)
class StudentRow:
    """Строка таблицы студентов по заданию."""

    student_id: UUID
    last_name: str
    first_name: str
    middle_name: str | None
    group_id: UUID
    group_name: str
    progress: Progress
