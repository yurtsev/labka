from collections.abc import Mapping, Sequence
from uuid import UUID

from src.api.feed.dto import FeedAnnouncement, FeedAssignment, FeedEntry
from src.core.db.dto.feed import FeedEntryKind, FeedEntryRef
from src.core.db.models.announcement import Announcement
from src.core.db.models.assignment import Assignment
from src.core.errors import InternalError
from src.core.grading.dto import Progress, Summary


class FeedPresenter:
    """Лента курса в порядке страницы: задания со статусами или сводками и объявления."""

    @staticmethod
    def entries(
        refs: Sequence[FeedEntryRef],
        assignments: Sequence[Assignment],
        announcements: Sequence[Announcement],
        progresses: Mapping[UUID, Progress],
        summaries: Mapping[UUID, Summary],
    ) -> tuple[FeedEntry, ...]:
        """Собирает записи ленты.

        Args:
            progresses: положение смотрящего студента по заданиям; у преподавателя пусто.
            summaries: сводки по заданиям для преподавателя; у студента пусто.
        """
        assignments_by_id = {item.id: item for item in assignments}
        announcements_by_id = {item.id: item for item in announcements}
        entries = []
        for ref in refs:
            match ref.kind:
                case FeedEntryKind.ASSIGNMENT:
                    assignment = assignments_by_id.get(ref.id)
                    if assignment is None:
                        raise InternalError({"assignment_id": str(ref.id)})
                    entries.append(
                        FeedEntry(
                            kind=ref.kind,
                            assignment=FeedPresenter._assignment(
                                assignment,
                                progresses.get(assignment.id),
                                summaries.get(assignment.id),
                            ),
                            announcement=None,
                        )
                    )
                case FeedEntryKind.ANNOUNCEMENT:
                    announcement = announcements_by_id.get(ref.id)
                    if announcement is None:
                        raise InternalError({"announcement_id": str(ref.id)})
                    entries.append(
                        FeedEntry(
                            kind=ref.kind,
                            assignment=None,
                            announcement=FeedAnnouncement(
                                id=announcement.id,
                                text=announcement.text,
                                created_at=announcement.created_at,
                                updated_at=announcement.updated_at,
                            ),
                        )
                    )
        return tuple(entries)

    @staticmethod
    def _assignment(
        assignment: Assignment, my_progress: Progress | None, summary: Summary | None
    ) -> FeedAssignment:
        return FeedAssignment(
            id=assignment.id,
            type=assignment.type,
            title=assignment.title,
            deadline_type=assignment.deadline_type,
            deadline_at=assignment.deadline_at,
            created_at=assignment.created_at,
            my_progress=my_progress,
            summary=summary,
        )
