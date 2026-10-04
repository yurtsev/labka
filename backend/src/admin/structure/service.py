from uuid import UUID, uuid7

from src.admin.exc.structure import (
    DepartmentInUseError,
    DepartmentNameTakenError,
    DepartmentNotFoundError,
    DirectionInUseError,
    DirectionNotFoundError,
    DirectionShortNameTakenError,
    FacultyInUseError,
    FacultyNameTakenError,
    FacultyNotFoundError,
)
from src.admin.structure.dto import DepartmentFields, DirectionFields, FacultyFields
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.department import Department
from src.core.db.models.direction import Direction
from src.core.db.models.faculty import Faculty
from src.core.db.uow import UnitOfWork


class AdminStructureService:
    """Структура вуза: подразделения, кафедры, направления.

    Повтор названия или сокращения — понятная ошибка, а не общий отказ БД. Пока на элемент
    ссылаются, удалять его нельзя; удаление уже отсутствующей записи — не ошибка.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_faculty(self, fields: FacultyFields) -> UUID:
        """Создаёт подразделение.

        Raises:
            FacultyNameTakenError: подразделение с таким названием уже есть.
        """
        faculty = Faculty(id=uuid7())
        self._apply_faculty(faculty, fields)
        self._uow.faculties.add(faculty)
        await self._commit_faculty()
        return faculty.id

    async def update_faculty(self, faculty_id: UUID, fields: FacultyFields) -> None:
        """Меняет подразделение.

        Raises:
            FacultyNotFoundError: подразделения нет.
            FacultyNameTakenError: подразделение с таким названием уже есть.
        """
        self._apply_faculty(await self._get_faculty(faculty_id), fields)
        await self._commit_faculty()

    async def create_department(self, fields: DepartmentFields) -> UUID:
        """Создаёт кафедру.

        Raises:
            FacultyNotFoundError: подразделения нет.
            DepartmentNameTakenError: в подразделении уже есть кафедра с таким названием.
        """
        department = Department(id=uuid7())
        await self._apply_department(department, fields)
        self._uow.departments.add(department)
        await self._commit_department()
        return department.id

    async def update_department(self, department_id: UUID, fields: DepartmentFields) -> None:
        """Меняет кафедру.

        Raises:
            DepartmentNotFoundError: кафедры нет.
            FacultyNotFoundError: подразделения нет.
            DepartmentNameTakenError: в подразделении уже есть кафедра с таким названием.
        """
        department = await self._uow.departments.get_by_id(department_id)
        if department is None:
            raise DepartmentNotFoundError({"department_id": str(department_id)})
        await self._apply_department(department, fields)
        await self._commit_department()

    async def create_direction(self, fields: DirectionFields) -> UUID:
        """Создаёт направление.

        Raises:
            FacultyNotFoundError: подразделения нет.
            DirectionShortNameTakenError: направление с таким сокращением уже есть.
        """
        direction = Direction(id=uuid7())
        await self._apply_direction(direction, fields)
        self._uow.directions.add(direction)
        await self._commit_direction()
        return direction.id

    async def update_direction(self, direction_id: UUID, fields: DirectionFields) -> None:
        """Меняет направление.

        Raises:
            DirectionNotFoundError: направления нет.
            FacultyNotFoundError: подразделения нет.
            DirectionShortNameTakenError: направление с таким сокращением уже есть.
        """
        direction = await self._uow.directions.get_by_id(direction_id)
        if direction is None:
            raise DirectionNotFoundError({"direction_id": str(direction_id)})
        await self._apply_direction(direction, fields)
        await self._commit_direction()

    async def delete_faculty(self, faculty_id: UUID) -> None:
        """Удаляет подразделение.

        Raises:
            FacultyInUseError: к подразделению привязаны кафедры или направления.
        """
        faculty = await self._uow.faculties.get_by_id(faculty_id)
        if faculty is None:
            return
        await self._uow.faculties.delete(faculty)
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint in {
                "fk_departments_faculty_id_faculties",
                "fk_directions_faculty_id_faculties",
            }:
                raise FacultyInUseError({"faculty_id": str(faculty_id)}) from exc
            raise

    async def delete_department(self, department_id: UUID) -> None:
        """Удаляет кафедру.

        Raises:
            DepartmentInUseError: на кафедре числятся преподаватели.
        """
        department = await self._uow.departments.get_by_id(department_id)
        if department is None:
            return
        await self._uow.departments.delete(department)
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "fk_users_department_id_departments":
                raise DepartmentInUseError({"department_id": str(department_id)}) from exc
            raise

    async def delete_direction(self, direction_id: UUID) -> None:
        """Удаляет направление.

        Raises:
            DirectionInUseError: у направления есть группы.
        """
        direction = await self._uow.directions.get_by_id(direction_id)
        if direction is None:
            return
        await self._uow.directions.delete(direction)
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "fk_groups_direction_id_directions":
                raise DirectionInUseError({"direction_id": str(direction_id)}) from exc
            raise

    async def _get_faculty(self, faculty_id: UUID) -> Faculty:
        faculty = await self._uow.faculties.get_by_id(faculty_id)
        if faculty is None:
            raise FacultyNotFoundError({"faculty_id": str(faculty_id)})
        return faculty

    async def _apply_department(self, department: Department, fields: DepartmentFields) -> None:
        department.faculty_id = (await self._get_faculty(fields.faculty_id)).id
        department.name = fields.name

    async def _apply_direction(self, direction: Direction, fields: DirectionFields) -> None:
        direction.faculty_id = (await self._get_faculty(fields.faculty_id)).id
        direction.short_name = fields.short_name
        direction.name = fields.name

    @staticmethod
    def _apply_faculty(faculty: Faculty, fields: FacultyFields) -> None:
        faculty.name = fields.name
        faculty.short_name = fields.short_name
        faculty.type = fields.type

    async def _commit_faculty(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_faculties_name":
                raise FacultyNameTakenError from exc
            raise

    async def _commit_department(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_departments_faculty_id_name":
                raise DepartmentNameTakenError from exc
            raise

    async def _commit_direction(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_directions_short_name":
                raise DirectionShortNameTakenError from exc
            raise
