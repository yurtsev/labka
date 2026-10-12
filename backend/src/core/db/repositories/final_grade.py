from typing import Any
from uuid import UUID

from sqlalchemy import Row, and_, select

from src.core.db.dto.final_grade import StudentFinalGrade
from src.core.db.dto.page import Page, PageRequest
from src.core.db.enums import UserRole
from src.core.db.models.course_exam import CourseExam
from src.core.db.models.course_group import CourseGroup
from src.core.db.models.final_grade import FinalGrade
from src.core.db.models.group import Group
from src.core.db.models.user import User
from src.core.db.repositories.base import BaseRepository


class FinalGradeRepository(BaseRepository[FinalGrade]):
    model = FinalGrade

    async def get(self, course_id: UUID, student_id: UUID) -> FinalGrade | None:
        """Итоговая оценка студента по курсу; объект перечитывается из БД."""
        query = (
            select(FinalGrade)
            .where(FinalGrade.course_id == course_id, FinalGrade.student_id == student_id)
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(query)

    async def exists_for_group(self, course_id: UUID, group_id: UUID) -> bool:
        """Есть ли итоговые результаты у студентов группы в курсе."""
        query = (
            select(FinalGrade.id)
            .join(User, User.id == FinalGrade.student_id)
            .where(FinalGrade.course_id == course_id, User.group_id == group_id)
            .limit(1)
        )
        return await self._session.scalar(query) is not None

    async def page_students(
        self, course_id: UUID, group_id: UUID | None, page: PageRequest
    ) -> Page[StudentFinalGrade]:
        """Активные студенты групп курса с итоговыми оценками, по алфавиту."""
        query = (
            select(
                User.id,
                User.last_name,
                User.first_name,
                User.middle_name,
                Group.id.label("group_id"),
                Group.name.label("group_name"),
                CourseExam.exam_type,
                FinalGrade.grade,
                FinalGrade.is_passed,
                FinalGrade.updated_at,
            )
            .select_from(User)
            .join(Group, Group.id == User.group_id)
            .join(CourseGroup, CourseGroup.group_id == User.group_id)
            .join(
                CourseExam,
                and_(CourseExam.course_id == course_id, CourseExam.group_id == User.group_id),
                isouter=True,
            )
            .join(
                FinalGrade,
                and_(FinalGrade.student_id == User.id, FinalGrade.course_id == course_id),
                isouter=True,
            )
            .where(
                CourseGroup.course_id == course_id,
                User.role == UserRole.STUDENT,
                User.is_active.is_(True),
            )
        )
        if group_id is not None:
            query = query.where(User.group_id == group_id)

        def build(row: Row[Any]) -> StudentFinalGrade:
            return StudentFinalGrade(
                student_id=row.id,
                last_name=row.last_name,
                first_name=row.first_name,
                middle_name=row.middle_name,
                group_id=row.group_id,
                group_name=row.group_name,
                exam_type=row.exam_type,
                grade=row.grade,
                passed=row.is_passed,
                graded_at=row.updated_at,
            )

        return await self._page_rows(query, page, (User.last_name, User.first_name, User.id), build)
