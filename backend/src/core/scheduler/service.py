import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.config import cfg
from src.core.db.uow import UnitOfWork
from src.core.notifications.reminders import DeadlineReminders
from src.core.notifications.service import NotificationService

log = logging.getLogger(__name__)


class SchedulerService:
    """Фоновые задачи приложения. Живёт в процессе, поэтому воркер должен быть один:
    иначе напоминания посчитаются несколько раз (повторы отсекает БД, но работа задвоится)."""

    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sessionmaker = sessionmaker
        self._scheduler = AsyncIOScheduler(timezone=UTC)

    def start(self) -> None:
        """Запускает планировщик; напоминания проверяются сразу и дальше по расписанию."""
        self._scheduler.add_job(
            self.remind_deadlines,
            IntervalTrigger(minutes=cfg.notifications.reminder_interval_minutes),
            id="deadline_reminders",
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now(UTC),
        )
        self._scheduler.start()

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def remind_deadlines(self) -> int:
        """Создаёт напоминания о дедлайнах в ближайшие сутки; возвращает число заданий."""
        async with self._sessionmaker() as session:
            uow = UnitOfWork(session)
            reminded = await DeadlineReminders(uow, NotificationService(uow)).send(
                datetime.now(UTC)
            )
        if reminded:
            log.info("notifications.deadline_reminders_sent", extra={"assignments": reminded})
        return reminded
