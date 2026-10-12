from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.repositories.announcement import AnnouncementRepository
from src.core.db.repositories.assignment import AssignmentRepository
from src.core.db.repositories.assignment_file import AssignmentFileRepository
from src.core.db.repositories.course import CourseRepository
from src.core.db.repositories.course_exam import CourseExamRepository
from src.core.db.repositories.course_material import CourseMaterialRepository
from src.core.db.repositories.course_material_file import CourseMaterialFileRepository
from src.core.db.repositories.department import DepartmentRepository
from src.core.db.repositories.direction import DirectionRepository
from src.core.db.repositories.extra_lesson import ExtraLessonRepository
from src.core.db.repositories.faculty import FacultyRepository
from src.core.db.repositories.final_grade import FinalGradeRepository
from src.core.db.repositories.group import GroupRepository
from src.core.db.repositories.group_invite import GroupInviteRepository
from src.core.db.repositories.notification import NotificationRepository
from src.core.db.repositories.personal_task import PersonalTaskRepository
from src.core.db.repositories.review import ReviewRepository
from src.core.db.repositories.schedule_rule import ScheduleRuleRepository
from src.core.db.repositories.session import SessionRepository
from src.core.db.repositories.submission import SubmissionRepository
from src.core.db.repositories.submission_file import SubmissionFileRepository
from src.core.db.repositories.user import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(self.session)
        self.sessions = SessionRepository(self.session)
        self.groups = GroupRepository(self.session)
        self.group_invites = GroupInviteRepository(self.session)
        self.directions = DirectionRepository(self.session)
        self.departments = DepartmentRepository(self.session)
        self.faculties = FacultyRepository(self.session)
        self.courses = CourseRepository(self.session)
        self.course_materials = CourseMaterialRepository(self.session)
        self.course_material_files = CourseMaterialFileRepository(self.session)
        self.announcements = AnnouncementRepository(self.session)
        self.assignments = AssignmentRepository(self.session)
        self.assignment_files = AssignmentFileRepository(self.session)
        self.submissions = SubmissionRepository(self.session)
        self.submission_files = SubmissionFileRepository(self.session)
        self.reviews = ReviewRepository(self.session)
        self.schedule_rules = ScheduleRuleRepository(self.session)
        self.extra_lessons = ExtraLessonRepository(self.session)
        self.personal_tasks = PersonalTaskRepository(self.session)
        self.course_exams = CourseExamRepository(self.session)
        self.final_grades = FinalGradeRepository(self.session)
        self.notifications = NotificationRepository(self.session)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
