from src.core.db.models.announcement import Announcement
from src.core.db.models.assignment import Assignment
from src.core.db.models.assignment_file import AssignmentFile
from src.core.db.models.base import Base
from src.core.db.models.course import Course
from src.core.db.models.course_group import CourseGroup
from src.core.db.models.department import Department
from src.core.db.models.direction import Direction
from src.core.db.models.faculty import Faculty
from src.core.db.models.group import Group
from src.core.db.models.group_invite import GroupInvite
from src.core.db.models.notification import Notification
from src.core.db.models.personal_task import PersonalTask
from src.core.db.models.review import Review
from src.core.db.models.schedule_rule import ScheduleRule
from src.core.db.models.session import Session
from src.core.db.models.submission import Submission
from src.core.db.models.submission_file import SubmissionFile
from src.core.db.models.teacher_group import TeacherGroup
from src.core.db.models.user import User

# Alembic's env.py imports Base from this package (not from .base directly).
# Every new model module must be imported here so it registers on Base.metadata
# and alembic autogenerate picks it up.

__all__ = [
    "Announcement",
    "Assignment",
    "AssignmentFile",
    "Base",
    "Course",
    "CourseGroup",
    "Department",
    "Direction",
    "Faculty",
    "Group",
    "GroupInvite",
    "Notification",
    "PersonalTask",
    "Review",
    "ScheduleRule",
    "Session",
    "Submission",
    "SubmissionFile",
    "TeacherGroup",
    "User",
]
