from collections.abc import Collection, Sequence
from uuid import UUID, uuid7

from src.core.db.dto.notification import NewNotification
from src.core.db.enums import NotificationType
from src.core.db.models.notification import Notification
from src.core.db.uow import UnitOfWork
from src.core.notifications.dto import CourseRef, NotificationView, Payload
from src.core.notifications.renderer import NotificationRenderer


class NotificationService:
    """Создание и показ личных уведомлений.

    Уведомления добавляются в ту же транзакцию, что и вызвавшее их действие: откатилось
    действие — откатились и они. Получателям их отправляет WebSocket, когда PostgreSQL
    сообщит о коммите.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def notify(
        self,
        recipients: Collection[UUID],
        type: NotificationType,
        payload: Payload,
        *,
        dedup_key: str | None = None,
    ) -> None:
        """Создаёт уведомление каждому получателю.

        Args:
            dedup_key: пока у получателя есть непрочитанное уведомление с этим ключом,
                новое не создаётся — например, при серии правок одного расписания.
        """
        data = payload.model_dump(mode="json", exclude_none=True)
        await self._uow.notifications.add_many(
            [
                NewNotification(
                    id=uuid7(),
                    user_id=user_id,
                    type=type.value,
                    data=data,
                    dedup_key=dedup_key,
                )
                for user_id in dict.fromkeys(recipients)
            ]
        )

    async def notify_course(
        self,
        course_id: UUID,
        type: NotificationType,
        payload: Payload,
        *,
        dedup_key: str | None = None,
    ) -> None:
        """Создаёт уведомление всем активным студентам групп курса."""
        recipients = await self._uow.users.course_student_ids(course_id)
        await self.notify(recipients, type, payload, dedup_key=dedup_key)

    async def notify_group(
        self,
        group_id: UUID,
        type: NotificationType,
        payload: Payload,
        *,
        dedup_key: str | None = None,
    ) -> None:
        """Создаёт уведомление всем активным студентам группы."""
        recipients = await self._uow.users.group_student_ids(group_id)
        await self.notify(recipients, type, payload, dedup_key=dedup_key)

    @staticmethod
    def view(notification: Notification) -> NotificationView:
        """Уведомление с заголовком, текстом и переходом, собранными по его типу."""
        payload = Payload.model_validate(notification.data)
        rendered = NotificationRenderer.render(notification.type, payload)
        course = (
            CourseRef(payload.course_id, payload.course_name)
            if payload.course_id is not None and payload.course_name is not None
            else None
        )
        return NotificationView(
            id=notification.id,
            type=notification.type,
            title=rendered.title,
            text=rendered.text,
            course=course,
            target=rendered.target,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )

    @staticmethod
    def views(notifications: Sequence[Notification]) -> tuple[NotificationView, ...]:
        return tuple(NotificationService.view(item) for item in notifications)
