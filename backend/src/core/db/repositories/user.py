from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.core.db.enums import UserRole
from src.core.db.models.course_group import CourseGroup
from src.core.db.models.session import Session
from src.core.db.models.user import User
from src.core.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def attached_avatar_keys(self, keys: Collection[str]) -> set[str]:
        """Какие из ключей уже стоят аватаркой у пользователя."""
        return await self._present(User.avatar_key, keys)

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))

    async def get_by_active_session(self, session_id: UUID, now: datetime) -> User | None:
        """Активный пользователь, у которого сессия не отозвана и не истекла."""
        query = (
            select(User)
            .join(Session, Session.user_id == User.id)
            .where(
                Session.id == session_id,
                Session.revoked_at.is_(None),
                Session.expires_at > now,
                User.is_active.is_(True),
            )
        )
        return await self._session.scalar(query)

    async def get_with_teaching_groups(self, user_id: UUID) -> User | None:
        query = select(User).where(User.id == user_id).options(selectinload(User.teaching_groups))
        return await self._session.scalar(query)

    async def get_with_affiliation(self, user_id: UUID) -> User | None:
        """Пользователь с группой (студент) и кафедрой (преподаватель)."""
        query = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.group), selectinload(User.department))
        )
        return await self._session.scalar(query)

    async def get_course_student(self, course_id: UUID, student_id: UUID) -> User | None:
        """Активный студент группы курса вместе с группой."""
        query = (
            select(User)
            .join(CourseGroup, CourseGroup.group_id == User.group_id)
            .where(
                User.id == student_id,
                CourseGroup.course_id == course_id,
                User.role == UserRole.STUDENT,
                User.is_active.is_(True),
            )
            .options(selectinload(User.group))
        )
        return await self._session.scalar(query)

    async def count_course_students(self, course_id: UUID) -> int:
        """Сколько активных студентов в группах курса."""
        query = (
            select(func.count())
            .select_from(User)
            .join(CourseGroup, CourseGroup.group_id == User.group_id)
            .where(
                CourseGroup.course_id == course_id,
                User.role == UserRole.STUDENT,
                User.is_active.is_(True),
            )
        )
        return await self._session.scalar(query) or 0
