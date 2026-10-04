from uuid import UUID, uuid7

from src.admin.exc.teachers import (
    DepartmentNotFoundError,
    TeacherEmailTakenError,
    TeacherGroupInactiveError,
    TeacherGroupNotFoundError,
    TeacherNotFoundError,
)
from src.admin.teachers.dto import CreatedTeacher, TeacherFields
from src.core.db.enums import UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.user import User
from src.core.db.uow import UnitOfWork
from src.core.security.service import SecurityService


class AdminTeacherService:
    """Преподаватели: создаёт их только админ, он же прикрепляет к ним группы."""

    def __init__(self, uow: UnitOfWork, security: SecurityService) -> None:
        self._uow = uow
        self._security = security

    async def create(self, fields: TeacherFields) -> CreatedTeacher:
        """Создаёт преподавателя со сгенерированным паролем.

        Returns:
            Id преподавателя и пароль в открытом виде: показать его можно только сейчас.

        Raises:
            DepartmentNotFoundError: кафедры нет.
            TeacherGroupNotFoundError: какой-то из групп нет.
            TeacherGroupInactiveError: среди групп есть неактивная.
            TeacherEmailTakenError: пользователь с этой почтой уже есть.
        """
        password = self._security.generate_password()
        teacher = User(
            id=uuid7(),
            password_hash=self._security.hash_password(password),
            role=UserRole.TEACHER,
            teaching_groups=[],
        )
        await self._apply_fields(teacher, fields)
        self._uow.users.add(teacher)
        await self._commit()
        return CreatedTeacher(teacher_id=teacher.id, password=password)

    async def update(self, teacher_id: UUID, fields: TeacherFields) -> None:
        """Меняет данные преподавателя и набор прикреплённых групп.

        Открепление группы не убирает её из уже созданных курсов: в новые курсы её
        добавить будет нельзя. Прикрепить можно только активную группу; уже прикреплённая
        группа, которую потом деактивировали, сохранению не мешает.

        Raises:
            TeacherNotFoundError: преподавателя нет.
            DepartmentNotFoundError: кафедры нет.
            TeacherGroupNotFoundError: какой-то из групп нет.
            TeacherGroupInactiveError: среди новых групп есть неактивная.
            TeacherEmailTakenError: пользователь с этой почтой уже есть.
        """
        teacher = await self._uow.users.get_with_teaching_groups(teacher_id)
        if teacher is None or teacher.role != UserRole.TEACHER:
            raise TeacherNotFoundError({"teacher_id": str(teacher_id)})
        await self._apply_fields(teacher, fields)
        await self._commit()

    async def _apply_fields(self, teacher: User, fields: TeacherFields) -> None:
        if await self._uow.departments.get_by_id(fields.department_id) is None:
            raise DepartmentNotFoundError({"department_id": str(fields.department_id)})
        groups = await self._uow.groups.get_many(fields.group_ids)
        if len(groups) != len(fields.group_ids):
            raise TeacherGroupNotFoundError
        attached_ids = {group.id for group in teacher.teaching_groups}
        inactive = [g for g in groups if not g.is_active and g.id not in attached_ids]
        if inactive:
            raise TeacherGroupInactiveError({"group_ids": sorted(str(g.id) for g in inactive)})
        teacher.last_name = fields.last_name
        teacher.first_name = fields.first_name
        teacher.middle_name = fields.middle_name
        teacher.email = fields.email
        teacher.department_id = fields.department_id
        teacher.teaching_groups = groups

    async def _commit(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_users_email":
                raise TeacherEmailTakenError from exc
            raise
