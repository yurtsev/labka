from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class NewNotification:
    """Уведомление, которое нужно создать; `dedup_key` — ключ против повтора, пока не прочитано."""

    id: UUID
    user_id: UUID
    type: str
    data: dict[str, object]
    dedup_key: str | None


@dataclass(frozen=True)
class ReminderTarget:
    """Студент, которому пора напомнить о дедлайне задания."""

    assignment_id: UUID
    assignment_title: str
    course_id: UUID
    course_name: str
    deadline_at: datetime
    student_id: UUID
