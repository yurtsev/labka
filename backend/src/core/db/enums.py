from enum import StrEnum


class FacultyType(StrEnum):
    FACULTY = "faculty"
    CENTER = "center"


class StudyLevel(StrEnum):
    BACHELOR = "bachelor"
    SPECIALIST = "specialist"
    MASTER = "master"

    @property
    def letter(self) -> str:
        """Буква уровня в названии группы: `Б` + `ВТ` + `26` + `01` = `БВТ2601`."""
        match self:
            case StudyLevel.BACHELOR:
                return "Б"
            case StudyLevel.SPECIALIST:
                return "С"
            case StudyLevel.MASTER:
                return "М"


class StudyForm(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    EXTRAMURAL = "extramural"


class UserRole(StrEnum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class ScaleType(StrEnum):
    RANGE = "range"
    BINARY = "binary"


class AssignmentType(StrEnum):
    LAB = "lab"
    PRACTICE = "practice"
    HW = "hw"


class DeadlineType(StrEnum):
    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


class ReviewVerdict(StrEnum):
    ACCEPTED = "accepted"
    REVISION = "revision"


class LessonType(StrEnum):
    LAB = "lab"
    PRACTICE = "practice"


class ExamType(StrEnum):
    """Форма итогового контроля по курсу."""

    CREDIT = "credit"
    GRADED_CREDIT = "graded_credit"
    EXAM = "exam"


class SemesterTerm(StrEnum):
    """Осенний семестр нечётный, весенний чётный."""

    AUTUMN = "autumn"
    SPRING = "spring"


class ScheduleRepeat(StrEnum):
    WEEKLY = "weekly"
    EVEN = "even"
    ODD = "odd"


class NotificationType(StrEnum):
    COURSE_ADDED = "course_added"
    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_UPDATED = "assignment_updated"
    MATERIAL_ADDED = "material_added"
    ANNOUNCEMENT_CREATED = "announcement_created"
    SCHEDULE_CHANGED = "schedule_changed"
    SUBMISSION_REVIEWED = "submission_reviewed"
    GRADE_CHANGED = "grade_changed"
    DEADLINE_REMINDER = "deadline_reminder"
    SUBMISSION_CREATED = "submission_created"
    EXAM_ASSIGNED = "exam_assigned"
    EXAM_CHANGED = "exam_changed"
    FINAL_RESULT_SET = "final_result_set"
