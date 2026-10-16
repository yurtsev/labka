from src.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError


class CourseNotFoundError(NotFoundError):
    code = "exams.course_not_found"
    message = "Курс не найден"


class CourseForbiddenError(ForbiddenError):
    code = "exams.course_forbidden"
    message = "Нет доступа к курсу"


class CourseArchivedError(ConflictError):
    code = "exams.course_archived"
    message = "Курс в архиве: изменения недоступны"


class ExamNotFoundError(NotFoundError):
    code = "exams.not_found"
    message = "Экзамен не найден"


class ExamAlreadyExistsError(ConflictError):
    code = "exams.already_exists"
    message = "У этой группы в курсе уже есть зачёт или экзамен"


class GroupNotInCourseError(RuleViolationError):
    code = "exams.group_not_in_course"
    message = "Этой группы нет в курсе"


class SlotNotFoundError(RuleViolationError):
    code = "exams.slot_not_found"
    message = "Такого окна пары нет в сетке"


class DateOutsideSemesterError(RuleViolationError):
    code = "exams.date_outside_semester"
    message = "Дата должна быть в семестре курса"
