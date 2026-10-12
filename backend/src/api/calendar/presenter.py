from collections.abc import Mapping, Sequence
from datetime import time
from uuid import UUID

from src.api.calendar.dto import (
    CalendarDeadline,
    CalendarExam,
    CalendarItem,
    CalendarLesson,
    CalendarTask,
    CourseRef,
    GroupRef,
)
from src.api.calendar.enums import CalendarItemKind
from src.core.db.models.assignment import Assignment
from src.core.db.models.course_exam import CourseExam
from src.core.db.models.personal_task import PersonalTask
from src.core.grading.enums import ProgressStatus
from src.core.schedule.dto import Occurrence
from src.core.schedule.service import ScheduleService
from src.core.utils.moscow_time import to_moscow


class CalendarPresenter:
    """События календаря: по дню и времени, затем занятия, экзамены, дедлайны, задачи."""

    @staticmethod
    def items(
        occurrences: Sequence[Occurrence],
        courses: Mapping[UUID, CourseRef],
        groups: Mapping[UUID, GroupRef],
        exams: Sequence[CourseExam],
        assignments: Sequence[Assignment],
        statuses: Mapping[UUID, ProgressStatus] | None,
        tasks: Sequence[PersonalTask],
    ) -> tuple[CalendarItem, ...]:
        """Собирает события.

        Args:
            courses: названия курсов занятий по id.
            groups: названия групп занятий по id.
            exams: экзамены за период.
            statuses: статус сдачи студента по заданиям; `None` у преподавателя.
        """
        found = [
            CalendarItem(
                kind=CalendarItemKind.LESSON,
                day=item.day,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                lesson=CalendarLesson(
                    course=courses[item.course_id],
                    group=groups[item.group_id],
                    lesson_type=item.lesson_type,
                    slot=ScheduleService.slot_number(item.starts_at, item.ends_at),
                    room=item.room,
                    is_extra=item.is_extra,
                ),
                exam=None,
                deadline=None,
                task=None,
            )
            for item in occurrences
        ]
        found.extend(
            CalendarItem(
                kind=CalendarItemKind.EXAM,
                day=exam.day,
                starts_at=exam.starts_at,
                ends_at=exam.ends_at,
                lesson=None,
                exam=CalendarExam(
                    course=CourseRef(exam.course.id, exam.course.name),
                    group=GroupRef(exam.group.id, exam.group.name),
                    exam_type=exam.exam_type,
                    slot=ScheduleService.slot_number(exam.starts_at, exam.ends_at),
                    room=exam.room,
                ),
                deadline=None,
                task=None,
            )
            for exam in exams
        )
        for assignment in assignments:
            if assignment.deadline_at is None:
                continue
            deadline = to_moscow(assignment.deadline_at)
            found.append(
                CalendarItem(
                    kind=CalendarItemKind.DEADLINE,
                    day=deadline.date(),
                    starts_at=deadline.time().replace(second=0, microsecond=0),
                    ends_at=None,
                    lesson=None,
                    exam=None,
                    deadline=CalendarDeadline(
                        assignment_id=assignment.id,
                        title=assignment.title,
                        type=assignment.type,
                        deadline_type=assignment.deadline_type,
                        course=CourseRef(assignment.course.id, assignment.course.name),
                        my_status=statuses[assignment.id] if statuses is not None else None,
                    ),
                    task=None,
                )
            )
        found.extend(
            CalendarItem(
                kind=CalendarItemKind.TASK,
                day=task.due_date,
                starts_at=task.due_time,
                ends_at=None,
                lesson=None,
                exam=None,
                deadline=None,
                task=CalendarTask(id=task.id, title=task.title, is_done=task.is_done),
            )
            for task in tasks
        )
        order = list(CalendarItemKind)
        return tuple(
            sorted(
                found,
                key=lambda item: (item.day, item.starts_at or time.min, order.index(item.kind)),
            )
        )
