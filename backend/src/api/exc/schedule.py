from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "schedule.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "schedule.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "schedule.course_archived"
    message = "Курс в архиве: изменения недоступны"


class RuleNotFoundError(NotFoundError):
    code = "schedule.rule_not_found"
    message = "Правило расписания не найдено"


class ExtraLessonNotFoundError(NotFoundError):
    code = "schedule.extra_lesson_not_found"
    message = "Разовое занятие не найдено"


class GroupNotInCourseError(RuleViolationError):
    code = "schedule.group_not_in_course"
    message = "Этой группы нет в курсе"


class SlotNotFoundError(RuleViolationError):
    code = "schedule.slot_not_found"
    message = "Такого окна пары нет в сетке"


class DateOutsideClassesError(RuleViolationError):
    code = "schedule.date_outside_classes"
    message = "Занятие должно быть в семестре курса, пока идут пары"
