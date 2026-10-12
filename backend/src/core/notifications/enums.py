from enum import StrEnum


class NotificationSection(StrEnum):
    """Раздел приложения, куда ведёт уведомление."""

    COURSE_FEED = "course_feed"
    ASSIGNMENT = "assignment"
    MATERIALS = "materials"
    SCHEDULE = "schedule"
    CALENDAR = "calendar"
    REVIEW = "review"
    FINAL_RESULT = "final_result"
