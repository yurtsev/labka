from src.core.di.access import AccessProvider
from src.core.di.admin import AdminProvider
from src.core.di.announcements import AnnouncementsProvider
from src.core.di.assignments import AssignmentsProvider
from src.core.di.auth import AuthProvider
from src.core.di.calendar import CalendarProvider
from src.core.di.courses import CoursesProvider
from src.core.di.exams import ExamsProvider
from src.core.di.feed import FeedProvider
from src.core.di.final_grades import FinalGradesProvider
from src.core.di.home import HomeProvider
from src.core.di.materials import MaterialsProvider
from src.core.di.notifications import NotificationsProvider
from src.core.di.profile import ProfileProvider
from src.core.di.reviews import ReviewsProvider
from src.core.di.s3 import S3Provider
from src.core.di.schedule import ScheduleProvider
from src.core.di.scheduler import SchedulerProvider
from src.core.di.security import SecurityProvider
from src.core.di.session import DbProvider
from src.core.di.submissions import SubmissionsProvider

__all__ = [
    "AccessProvider",
    "AnnouncementsProvider",
    "AssignmentsProvider",
    "FeedProvider",
    "ReviewsProvider",
    "SubmissionsProvider",
    "AdminProvider",
    "AuthProvider",
    "HomeProvider",
    "NotificationsProvider",
    "SchedulerProvider",
    "ExamsProvider",
    "FinalGradesProvider",
    "CalendarProvider",
    "ScheduleProvider",
    "CoursesProvider",
    "DbProvider",
    "MaterialsProvider",
    "ProfileProvider",
    "S3Provider",
    "SecurityProvider",
]
