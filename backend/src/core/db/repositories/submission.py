from collections.abc import Collection
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Row,
    Select,
    SQLColumnExpression,
    Subquery,
    and_,
    case,
    exists,
    false,
    func,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import aliased, selectinload

from src.core.db.dto.page import Page, PageRequest
from src.core.db.dto.progress import ProgressRow, StudentProgress, StudentProgressFilter, SummaryRow
from src.core.db.dto.submission import PendingFilter
from src.core.db.enums import ReviewVerdict, UserRole
from src.core.db.models.assignment import Assignment
from src.core.db.models.course import Course
from src.core.db.models.course_group import CourseGroup
from src.core.db.models.group import Group
from src.core.db.models.review import Review
from src.core.db.models.submission import Submission
from src.core.db.models.user import User
from src.core.db.repositories.base import BaseRepository
from src.core.grading.enums import ProgressStatus


class SubmissionRepository(BaseRepository[Submission]):
    model = Submission

    async def progress(
        self, assignment_ids: Collection[UUID], student_ids: Collection[UUID] | None
    ) -> dict[tuple[UUID, UUID], ProgressRow]:
        """Положение студентов по заданиям; у кого нет попыток, тех в результате нет.

        `student_ids=None` — всех студентов.
        """
        if not assignment_ids:
            return {}
        progress = self._progress(assignment_ids)
        query = select(progress)
        if student_ids is not None:
            query = query.where(progress.c.student_id.in_(student_ids))
        rows = await self._session.execute(query)
        found = [self._progress_row(row) for row in rows.all()]
        return {(item.assignment_id, item.student_id): item for item in found}

    async def summaries(
        self, course_id: UUID, assignment_ids: Collection[UUID]
    ) -> dict[UUID, SummaryRow]:
        """Сводки по заданиям среди студентов курса; попытки ушедших студентов не считаются."""
        if not assignment_ids:
            return {}
        progress = self._progress(assignment_ids)
        query = (
            select(
                progress.c.assignment_id,
                func.count().label("submitted"),
                func.count().filter(progress.c.status == ProgressStatus.ON_REVIEW.value),
                func.count().filter(progress.c.status == ProgressStatus.ACCEPTED.value),
            )
            .select_from(progress)
            .join(User, User.id == progress.c.student_id)
            .join(CourseGroup, CourseGroup.group_id == User.group_id)
            .where(
                CourseGroup.course_id == course_id,
                User.role == UserRole.STUDENT,
                User.is_active.is_(True),
            )
            .group_by(progress.c.assignment_id)
        )
        rows = await self._session.execute(query)
        return {
            row[0]: SummaryRow(
                assignment_id=row[0], submitted=row[1], on_review=row[2], accepted=row[3]
            )
            for row in rows.all()
        }

    async def page_students(
        self, course_id: UUID, search: StudentProgressFilter, page: PageRequest
    ) -> Page[StudentProgress]:
        """Студенты курса по заданию с положением по нему, по алфавиту."""
        progress = self._progress([search.assignment_id])
        status = func.coalesce(progress.c.status, ProgressStatus.NOT_SUBMITTED.value)
        query = (
            select(
                User.id,
                User.last_name,
                User.first_name,
                User.middle_name,
                Group.id.label("group_id"),
                Group.name.label("group_name"),
                status.label("status"),
                func.coalesce(progress.c.attempts, 0).label("attempts"),
                progress.c.last_submitted_at,
                func.coalesce(progress.c.last_is_late, false()).label("last_is_late"),
                progress.c.grade_score,
                progress.c.grade_passed,
            )
            .select_from(User)
            .join(Group, Group.id == User.group_id)
            .join(CourseGroup, CourseGroup.group_id == User.group_id)
            .join(progress, progress.c.student_id == User.id, isouter=True)
            .where(
                CourseGroup.course_id == course_id,
                User.role == UserRole.STUDENT,
                User.is_active.is_(True),
            )
        )
        if search.group_id is not None:
            query = query.where(User.group_id == search.group_id)
        if search.status is not None:
            query = query.where(status == search.status.value)

        def build(row: Row[Any]) -> StudentProgress:
            return StudentProgress(
                student_id=row.id,
                last_name=row.last_name,
                first_name=row.first_name,
                middle_name=row.middle_name,
                group_id=row.group_id,
                group_name=row.group_name,
                progress=ProgressRow(
                    assignment_id=search.assignment_id,
                    student_id=row.id,
                    status=ProgressStatus(row.status),
                    attempts=row.attempts,
                    last_submitted_at=row.last_submitted_at,
                    last_is_late=row.last_is_late,
                    grade_score=row.grade_score,
                    grade_passed=row.grade_passed,
                ),
            )

        return await self._page_rows(query, page, (User.last_name, User.first_name, User.id), build)

    async def history(self, assignment_id: UUID, student_id: UUID) -> list[Submission]:
        """Попытки студента по заданию с файлами и проверками, новые первыми."""
        query = (
            select(Submission)
            .where(Submission.assignment_id == assignment_id, Submission.student_id == student_id)
            .options(selectinload(Submission.files), selectinload(Submission.review))
            .order_by(Submission.number.desc())
            .execution_options(populate_existing=True)
        )
        return list(await self._session.scalars(query))

    async def last_number(self, assignment_id: UUID, student_id: UUID) -> int:
        query = select(func.max(Submission.number)).where(
            Submission.assignment_id == assignment_id, Submission.student_id == student_id
        )
        return await self._session.scalar(query) or 0

    async def get_with_review(self, submission_id: UUID) -> Submission | None:
        """Попытка с проверкой и файлами; объект из сессии перечитывается из БД."""
        query = (
            select(Submission)
            .where(Submission.id == submission_id)
            .options(selectinload(Submission.review), selectinload(Submission.files))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def page_pending(self, search: PendingFilter, page: PageRequest) -> Page[Submission]:
        """Очередь на проверку преподавателя, старые попытки первыми."""
        query = self._pending().where(Course.teacher_id == search.teacher_id)
        if search.course_id is not None:
            query = query.where(Course.id == search.course_id)
        if search.assignment_id is not None:
            query = query.where(Assignment.id == search.assignment_id)
        query = query.options(
            selectinload(Submission.student).selectinload(User.group),
            selectinload(Submission.assignment).selectinload(Assignment.course),
        )
        return await self._page(query, page, Submission.created_at, Submission.id)

    async def count_pending_for_teacher(self, teacher_id: UUID) -> int:
        """Сколько попыток ждут проверки по всем неархивным курсам преподавателя."""
        query = select(func.count()).select_from(
            self._pending().where(Course.teacher_id == teacher_id).subquery()
        )
        return await self._session.scalar(query) or 0

    async def list_pending_deadlines(
        self, student_id: UUID, group_id: UUID, now: datetime, limit: int
    ) -> list[Assignment]:
        """Ближайшие по сроку задания студента, по которым ещё нужно сдавать.

        Дедлайн не раньше `now`, в неархивных курсах его группы; работа не сдана или
        возвращена на доработку. С курсами и преподавателями.
        """
        progress = self._progress(
            select(Assignment.id)
            .join(CourseGroup, CourseGroup.course_id == Assignment.course_id)
            .where(CourseGroup.group_id == group_id)
        )
        status = func.coalesce(progress.c.status, ProgressStatus.NOT_SUBMITTED.value)
        query = (
            select(Assignment)
            .join(Course, Course.id == Assignment.course_id)
            .join(CourseGroup, CourseGroup.course_id == Course.id)
            .join(
                progress,
                and_(
                    progress.c.assignment_id == Assignment.id,
                    progress.c.student_id == student_id,
                ),
                isouter=True,
            )
            .where(
                CourseGroup.group_id == group_id,
                Course.is_archived.is_(False),
                Assignment.deadline_at >= now,
                status.in_([ProgressStatus.NOT_SUBMITTED.value, ProgressStatus.REVISION.value]),
            )
            .options(selectinload(Assignment.course).selectinload(Course.teacher))
            .order_by(Assignment.deadline_at, Assignment.id)
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    async def count_pending_by_course(self, course_ids: Collection[UUID]) -> dict[UUID, int]:
        """Сколько попыток ждут проверки в каждом из курсов."""
        if not course_ids:
            return {}
        query = (
            self._pending()
            .with_only_columns(Course.id, func.count(Submission.id))
            .where(Course.id.in_(course_ids))
            .group_by(Course.id)
        )
        rows = await self._session.execute(query)
        return dict(rows.tuples().all())

    @staticmethod
    def _progress(assignment_ids: Collection[UUID] | Select[Any]) -> Subquery:
        """Положение каждого студента по заданиям: одна строка на пару «задание + студент».

        «Принято» — если принята любая попытка; иначе «на проверке», когда последняя попытка
        без проверки, и «на доработку», когда проверена. Оценка — из последней проверенной
        попытки, где она выставлена.
        """
        newest_first = Submission.number.desc()
        has_grade = or_(Review.score.is_not(None), Review.is_passed.is_not(None))

        def last(column: SQLColumnExpression[Any]) -> SQLColumnExpression[Any]:
            return func.array_agg(aggregate_order_by(column, newest_first))[1]

        def last_graded(column: SQLColumnExpression[Any]) -> SQLColumnExpression[Any]:
            return func.array_agg(aggregate_order_by(column, has_grade.desc(), newest_first))[1]

        accepted = func.coalesce(func.bool_or(Review.verdict == ReviewVerdict.ACCEPTED), false())
        status = case(
            (accepted, ProgressStatus.ACCEPTED.value),
            (~last(Review.id.is_not(None)), ProgressStatus.ON_REVIEW.value),
            else_=ProgressStatus.REVISION.value,
        )
        return (
            select(
                Submission.assignment_id,
                Submission.student_id,
                status.label("status"),
                func.count().label("attempts"),
                last(Submission.created_at).label("last_submitted_at"),
                last(Submission.is_late).label("last_is_late"),
                last_graded(Review.score).label("grade_score"),
                last_graded(Review.is_passed).label("grade_passed"),
            )
            .join(Review, Review.submission_id == Submission.id, isouter=True)
            .where(Submission.assignment_id.in_(assignment_ids))
            .group_by(Submission.assignment_id, Submission.student_id)
            .subquery()
        )

    @staticmethod
    def _progress_row(row: Row[Any]) -> ProgressRow:
        return ProgressRow(
            assignment_id=row.assignment_id,
            student_id=row.student_id,
            status=ProgressStatus(row.status),
            attempts=row.attempts,
            last_submitted_at=row.last_submitted_at,
            last_is_late=row.last_is_late,
            grade_score=row.grade_score,
            grade_passed=row.grade_passed,
        )

    @staticmethod
    def _pending() -> Select[tuple[Submission]]:
        """Ждут проверки: последняя попытка студента без проверки, студент активен и сейчас
        в группе курса, курс не в архиве."""
        newer = aliased(Submission)
        return (
            select(Submission)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .join(Course, Course.id == Assignment.course_id)
            .join(User, User.id == Submission.student_id)
            .join(
                CourseGroup,
                and_(CourseGroup.course_id == Course.id, CourseGroup.group_id == User.group_id),
            )
            .where(
                Course.is_archived.is_(False),
                User.is_active.is_(True),
                ~exists().where(Review.submission_id == Submission.id),
                ~exists().where(
                    newer.assignment_id == Submission.assignment_id,
                    newer.student_id == Submission.student_id,
                    newer.number > Submission.number,
                ),
            )
        )
