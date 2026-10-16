from datetime import UTC, datetime
from uuid import UUID

from src.api.exc.feed import CourseForbiddenError, CourseNotFoundError
from src.api.feed.dto import FeedEntry
from src.api.feed.presenter import FeedPresenter
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.dto.feed import FeedEntryKind
from src.core.db.dto.page import Page, PageRequest
from src.core.db.enums import AssignmentType, UserRole
from src.core.db.uow import UnitOfWork
from src.core.grading.dto import Progress, Summary
from src.core.grading.service import GradingService
from src.core.security.dto import CurrentUser


class FeedService:
    """Лента курса: задания и объявления вперемешку, новые первыми."""

    def __init__(self, uow: UnitOfWork, access: AccessService) -> None:
        self._uow = uow
        self._access = access

    async def feed(
        self,
        user: CurrentUser,
        course_id: UUID,
        assignment_type: AssignmentType | None,
        page: PageRequest,
    ) -> Page[FeedEntry]:
        """Страница ленты; с фильтром по типу задания — только задания этого типа.

        Студент видит у заданий свой статус и текущую оценку, преподаватель — сводку.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
        """
        try:
            await self._access.readable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc

        refs = await self._uow.courses.feed_page(course_id, assignment_type, page)
        assignment_ids = [ref.id for ref in refs.items if ref.kind == FeedEntryKind.ASSIGNMENT]
        announcement_ids = [ref.id for ref in refs.items if ref.kind == FeedEntryKind.ANNOUNCEMENT]
        assignments = await self._uow.assignments.get_many(assignment_ids)
        announcements = await self._uow.announcements.get_many(announcement_ids)
        progresses: dict[UUID, Progress] = {}
        summaries: dict[UUID, Summary] = {}
        if user.role == UserRole.STUDENT:
            rows = await self._uow.submissions.progress(assignment_ids, [user.user_id])
            now = datetime.now(UTC)
            progresses = {
                assignment.id: GradingService.progress(
                    rows.get((assignment.id, user.user_id)), assignment, now
                )
                for assignment in assignments
            }
        else:
            students = await self._uow.users.count_course_students(course_id)
            sums = await self._uow.submissions.summaries(course_id, assignment_ids)
            summaries = {
                assignment_id: GradingService.summary(students, sums.get(assignment_id))
                for assignment_id in assignment_ids
            }
        return refs.map(
            FeedPresenter.entries(refs.items, assignments, announcements, progresses, summaries)
        )
