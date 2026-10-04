from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from src.core.db.models.session import Session
from src.core.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    model = Session

    async def get_for_update(self, session_id: UUID) -> Session | None:
        """Сессия с блокировкой строки: параллельные refresh одной сессии идут по очереди."""
        query = select(Session).where(Session.id == session_id).with_for_update()
        return await self._session.scalar(query)

    async def revoke_all_for_user(
        self, user_id: UUID, now: datetime, except_session_id: UUID | None = None
    ) -> None:
        query = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        if except_session_id is not None:
            query = query.where(Session.id != except_session_id)
        await self._session.execute(query)
