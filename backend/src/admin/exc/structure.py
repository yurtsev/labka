from src.core.errors import ConflictError, NotFoundError


class FacultyInUseError(ConflictError):
    code = "admin.faculty_in_use"
    message = "Нельзя удалить: к подразделению привязаны кафедры или направления"


class DepartmentInUseError(ConflictError):
    code = "admin.department_in_use"
    message = "Нельзя удалить: на кафедре числятся преподаватели"


class DirectionInUseError(ConflictError):
    code = "admin.direction_in_use"
    message = "Нельзя удалить: у направления есть группы"


class FacultyNotFoundError(NotFoundError):
    code = "admin.faculty_not_found"
    message = "Подразделение не найдено"


class DepartmentNotFoundError(NotFoundError):
    code = "admin.department_not_found"
    message = "Кафедра не найдена"


class DirectionNotFoundError(NotFoundError):
    code = "admin.direction_not_found"
    message = "Направление не найдено"


class FacultyNameTakenError(ConflictError):
    code = "admin.faculty_name_taken"
    message = "Подразделение с таким названием уже есть"


class DepartmentNameTakenError(ConflictError):
    code = "admin.department_name_taken"
    message = "В этом подразделении уже есть кафедра с таким названием"


class DirectionShortNameTakenError(ConflictError):
    code = "admin.direction_short_name_taken"
    message = "Направление с таким сокращением уже есть"
