from enum import StrEnum


class CalendarItemKind(StrEnum):
    LESSON = "lesson"
    EXAM = "exam"
    DEADLINE = "deadline"
    TASK = "task"
