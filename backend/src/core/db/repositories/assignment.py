from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, exists, func, select, union_all, update
from sqlalchemy.orm import selectinload

from src.core.db.dto.notification import ReminderTarget
from src.core.db.enums import NotificationType, UserRole
from src.core.db.models.assignment import Assignment
from src.core.db.models.assignment_file import AssignmentFile
from src.core.db.models.course import Course
from src.core.db.models.course_group import CourseGroup
from src.core.db.models.notification import Notification
from src.core.db.models.submission import Submission
from src.core.db.models.submission_file import SubmissionFile
from src.core.db.models.user import User
from src.core.db.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[Assignment]):
    model = Assignment

    async def get_with_files(self, assignment_id: UUID) -> Assignment | None:
        """Задание с файлами; уже загруженный в сессию объект перечитывается из БД."""
        query = (
            select(Assignment)
            .where(Assignment.id == assignment_id)
            .options(selectinload(Assignment.files))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def get_many(self, assignment_ids: Collection[UUID]) -> list[Assignment]:
        if not assignment_ids:
            return []
        query = select(Assignment).where(Assignment.id.in_(assignment_ids))
        return list(await self._session.scalars(query))

    async def list_with_deadline(
        self, teacher_id: UUID | None, group_id: UUID | None, first: datetime, last: datetime
    ) -> list[Assignment]:
        """Задания с дедлайном в `[first, last)` в неархивных курсах с курсами.

        Курсы преподавателя (`teacher_id`) или курсы группы студента (`group_id`).
        """
        query = (
            select(Assignment)
            .join(Course, Course.id == Assignment.course_id)
            .where(
                Course.is_archived.is_(False),
                Assignment.deadline_at >= first,
                Assignment.deadline_at < last,
            )
            .options(selectinload(Assignment.course))
            .order_by(Assignment.deadline_at, Assignment.id)
        )
        if teacher_id is not None:
            query = query.where(Course.teacher_id == teacher_id)
        if group_id is not None:
            query = query.join(CourseGroup, CourseGroup.course_id == Course.id).where(
                CourseGroup.group_id == group_id
            )
        return list(await self._session.scalars(query))

    async def list_reminder_targets(self, now: datetime, until: datetime) -> list[ReminderTarget]:
        """Студенты, которым пора напомнить о дедлайне в `(now, until]`.

        Задание с дедлайном в неархивном курсе, у студента нет ни одной попытки и напоминание
        по заданию ему ещё не создавалось.
        """
        query = (
            select(
                Assignment.id,
                Assignment.title,
                Course.id,
                Course.name,
                Assignment.deadline_at,
                User.id,
            )
            .join(Course, Course.id == Assignment.course_id)
            .join(CourseGroup, CourseGroup.course_id == Course.id)
            .join(User, User.group_id == CourseGroup.group_id)
            .where(
                Course.is_archived.is_(False),
                Assignment.deadline_at > now,
                Assignment.deadline_at <= until,
                User.role == UserRole.STUDENT,
                User.is_active.is_(True),
                ~exists().where(
                    Submission.assignment_id == Assignment.id, Submission.student_id == User.id
                ),
                ~exists().where(
                    Notification.user_id == User.id,
                    Notification.type == NotificationType.DEADLINE_REMINDER,
                    Notification.data["assignment_id"].astext == func.cast(Assignment.id, String),
                    Notification.data["deadline_at"].astext.cast(DateTime(timezone=True))
                    == Assignment.deadline_at,
                ),
            )
            .order_by(Assignment.deadline_at, Assignment.id, User.id)
        )
        rows = await self._session.execute(query)
        return [
            ReminderTarget(
                assignment_id=row[0],
                assignment_title=row[1],
                course_id=row[2],
                course_name=row[3],
                deadline_at=row[4],
                student_id=row[5],
            )
            for row in rows.all()
        ]

    async def count_unsubmitted_by_course(
        self, student_id: UUID, course_ids: Collection[UUID]
    ) -> dict[UUID, int]:
        """Сколько заданий в каждом курсе студент ещё не сдавал; без попыток — 0."""
        if not course_ids:
            return {}
        query = (
            select(Assignment.course_id, func.count(Assignment.id))
            .where(
                Assignment.course_id.in_(course_ids),
                ~exists().where(
                    Submission.assignment_id == Assignment.id, Submission.student_id == student_id
                ),
            )
            .group_by(Assignment.course_id)
        )
        found = dict((await self._session.execute(query)).tuples().all())
        return {course_id: found.get(course_id, 0) for course_id in course_ids}

    async def count_submissions(self, assignment_id: UUID) -> int:
        query = select(func.count(Submission.id)).where(Submission.assignment_id == assignment_id)
        return await self._session.scalar(query) or 0

    async def file_keys(self, assignment_id: UUID) -> list[str]:
        """Ключи всех файлов задания в S3: файлы преподавателя и файлы всех попыток."""
        own = select(AssignmentFile.file_key).where(AssignmentFile.assignment_id == assignment_id)
        submitted = (
            select(SubmissionFile.file_key)
            .join(Submission, Submission.id == SubmissionFile.submission_id)
            .where(Submission.assignment_id == assignment_id)
        )
        return list(await self._session.scalars(union_all(own, submitted)))

    async def inherits_scale_with_submissions(self, course_id: UUID) -> bool:
        """Есть ли в курсе задание со шкалой курса, по которому уже есть попытки."""
        query = select(
            exists().where(
                Assignment.course_id == course_id,
                Assignment.scale_type.is_(None),
                exists().where(Submission.assignment_id == Assignment.id),
            )
        )
        return bool(await self._session.scalar(query))

    async def touch(self, assignment_id: UUID) -> None:
        """Отмечает, что задание изменилось, хотя его собственные поля прежние."""
        query = (
            update(Assignment).where(Assignment.id == assignment_id).values(updated_at=func.now())
        )
        await self._session.execute(query)
