from uuid import UUID, uuid7

from src.api.announcements.dto import Announcement
from src.api.exc.announcements import (
    AnnouncementNotFoundError,
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
)
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.models.announcement import Announcement as AnnouncementModel
from src.core.db.models.course import Course
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.security.dto import CurrentUser


class AnnouncementService:
    """Объявления в ленте курса: текст в markdown, пишет и правит преподаватель."""

    def __init__(self, uow: UnitOfWork, access: AccessService) -> None:
        self._uow = uow
        self._access = access

    async def create(self, user: CurrentUser, course_id: UUID, text: str) -> Announcement:
        """Публикует объявление в ленте курса.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
        """
        await self._editable(user, course_id)
        announcement = AnnouncementModel(id=uuid7(), course_id=course_id, text=text)
        self._uow.announcements.add(announcement)
        await self._uow.commit()
        return await self._reload(announcement.id)

    async def update(
        self, user: CurrentUser, course_id: UUID, announcement_id: UUID, text: str
    ) -> Announcement:
        """Меняет текст объявления.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AnnouncementNotFoundError: объявления нет в этом курсе.
        """
        await self._editable(user, course_id)
        announcement = await self._get(course_id, announcement_id)
        announcement.text = text
        await self._uow.commit()
        return await self._reload(announcement.id)

    async def delete(self, user: CurrentUser, course_id: UUID, announcement_id: UUID) -> None:
        """Удаляет объявление.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AnnouncementNotFoundError: объявления нет в этом курсе.
        """
        await self._editable(user, course_id)
        await self._uow.announcements.delete(await self._get(course_id, announcement_id))
        await self._uow.commit()

    async def _get(self, course_id: UUID, announcement_id: UUID) -> AnnouncementModel:
        announcement = await self._uow.announcements.get_by_id(announcement_id)
        if announcement is None or announcement.course_id != course_id:
            raise AnnouncementNotFoundError({"announcement_id": str(announcement_id)})
        return announcement

    async def _reload(self, announcement_id: UUID) -> Announcement:
        announcement = await self._uow.announcements.get_fresh(announcement_id)
        if announcement is None:
            raise InternalError({"announcement_id": str(announcement_id)})
        return Announcement(
            id=announcement.id,
            text=announcement.text,
            created_at=announcement.created_at,
            updated_at=announcement.updated_at,
        )

    async def _editable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.editable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc
        except access_exc.CourseArchivedError as exc:
            raise CourseArchivedError({"course_id": str(course_id)}) from exc
