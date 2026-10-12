from datetime import datetime, timedelta
from itertools import groupby

from src.config import cfg
from src.core.db.enums import NotificationType
from src.core.db.uow import UnitOfWork
from src.core.notifications.dto import Payload
from src.core.notifications.service import NotificationService


class DeadlineReminders:
    """Напоминания студентам, не сдавшим работу, за сутки до дедлайна."""

    def __init__(self, uow: UnitOfWork, notifications: NotificationService) -> None:
        self._uow = uow
        self._notifications = notifications

    async def send(self, now: datetime) -> int:
        """Создаёт напоминания по заданиям с дедлайном в ближайшие сутки и фиксирует их.

        Повторное напоминание по тому же заданию студенту не создаётся, даже если дедлайн
        потом сдвинули. Возвращает число заданий, по которым напомнили.
        """
        until = now + timedelta(hours=cfg.notifications.reminder_window_hours)
        targets = await self._uow.assignments.list_reminder_targets(now, until)
        reminded = 0
        for _, group in groupby(targets, key=lambda item: item.assignment_id):
            students = list(group)
            first = students[0]
            await self._notifications.notify(
                [item.student_id for item in students],
                NotificationType.DEADLINE_REMINDER,
                Payload(
                    course_id=first.course_id,
                    course_name=first.course_name,
                    assignment_id=first.assignment_id,
                    assignment_title=first.assignment_title,
                    deadline_at=first.deadline_at,
                ),
            )
            reminded += 1
        await self._uow.commit()
        return reminded
