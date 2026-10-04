from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.db.models.session import Session
from src.core.db.models.user import User
from src.core.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

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
