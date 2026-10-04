from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.repositories.course import CourseRepository
from src.core.db.repositories.department import DepartmentRepository
from src.core.db.repositories.direction import DirectionRepository
from src.core.db.repositories.faculty import FacultyRepository
from src.core.db.repositories.group import GroupRepository
from src.core.db.repositories.group_invite import GroupInviteRepository
from src.core.db.repositories.session import SessionRepository
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

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
