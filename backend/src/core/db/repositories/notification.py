from collections.abc import Collection, Sequence
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from src.core.db.dto.notification import NewNotification
from src.core.db.dto.page import Page, PageRequest
from src.core.db.models.notification import Notification
from src.core.db.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def add_many(self, items: Sequence[NewNotification]) -> None:
        """Создаёт уведомления: по одному запросу на обычные и на дедуплицируемые.

        Если у получателя уже есть непрочитанное уведомление с тем же `dedup_key`, оно
        обновляется (свежие данные, время «сейчас»), а не создаётся второе. Повторное
        напоминание о дедлайне молча пропускается. Конфликт решает сама БД.
        """
        keyed = [item for item in items if item.dedup_key is not None]
        plain = [item for item in items if item.dedup_key is None]
        if plain:
            await self._session.execute(
                insert(Notification).values(self._rows(plain)).on_conflict_do_nothing()
            )
        if keyed:
            statement = insert(Notification).values(self._rows(keyed))
            await self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=["user_id", "dedup_key"],
                    index_where=text("NOT is_read AND dedup_key IS NOT NULL"),
                    set_={"data": statement.excluded.data, "created_at": func.now()},
                )
            )

    @staticmethod
    def _rows(items: Sequence[NewNotification]) -> list[dict[str, object]]:
        return [
            {
                "id": item.id,
                "user_id": item.user_id,
                "type": item.type,
                "data": item.data,
                "dedup_key": item.dedup_key,
            }
            for item in items
        ]

    async def page_for_user(
        self, user_id: UUID, unread_only: bool, page: PageRequest
    ) -> Page[Notification]:
        """Уведомления пользователя, новые первыми."""
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        return await self._page(query, page, Notification.created_at.desc(), Notification.id.desc())

    async def get_many(self, notification_ids: Collection[UUID]) -> list[Notification]:
        if not notification_ids:
            return []
        query = select(Notification).where(Notification.id.in_(notification_ids))
        return list(await self._session.scalars(query))

    async def count_unread(self, user_id: UUID) -> int:
        query = select(func.count()).where(
            Notification.user_id == user_id, Notification.is_read.is_(False)
        )
        return await self._session.scalar(query) or 0

    async def count_unread_by_user(self, user_ids: Collection[UUID]) -> dict[UUID, int]:
        """Сколько непрочитанных у каждого из пользователей; у кого нет — 0."""
        if not user_ids:
            return {}
        query = (
            select(Notification.user_id, func.count())
            .where(Notification.user_id.in_(user_ids), Notification.is_read.is_(False))
            .group_by(Notification.user_id)
        )
        found = dict((await self._session.execute(query)).tuples().all())
        return {user_id: found.get(user_id, 0) for user_id in user_ids}

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        """Отмечает уведомление прочитанным; `False`, если такого у пользователя нет."""
        query = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
            .returning(Notification.id)
        )
        return await self._session.scalar(query) is not None

    async def mark_all_read(self, user_id: UUID) -> int:
        """Отмечает прочитанными все непрочитанные уведомления; возвращает их число."""
        query = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
            .returning(Notification.id)
        )
        return len((await self._session.scalars(query)).all())
