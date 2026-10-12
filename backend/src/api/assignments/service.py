from collections.abc import Sequence
from uuid import UUID, uuid7

from src.api.assignments.dto import (
    Assignment,
    AssignmentFields,
    AssignmentFile,
    StudentRow,
    StudentRowsFilter,
    UploadedFile,
)
from src.api.exc.assignments import (
    AssignmentFileNotFoundError,
    AssignmentNotFoundError,
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    FileAlreadyAttachedError,
    FileNotUploadedError,
    FileTooLargeError,
    ForeignFileKeyError,
    ScaleLockedError,
    TeacherOnlyError,
)
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.dto.page import Page, PageRequest
from src.core.db.dto.progress import StudentProgressFilter
from src.core.db.enums import UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.assignment import Assignment as AssignmentModel
from src.core.db.models.assignment_file import AssignmentFile as AssignmentFileModel
from src.core.db.models.course import Course
from src.core.db.uow import UnitOfWork
from src.core.grading.dto import Progress, Summary
from src.core.grading.service import GradingService
from src.core.s3.dto import PresignedUpload
from src.core.s3.exc import S3FileTooLargeError, S3ObjectNotFoundError
from src.core.s3.service import S3Storage
from src.core.security.dto import CurrentUser


class AssignmentService:
    """Задания курса: создаёт и правит преподаватель, студенты курса видят их сразу."""

    def __init__(self, uow: UnitOfWork, access: AccessService, storage: S3Storage) -> None:
        self._uow = uow
        self._access = access
        self._storage = storage

    async def start_upload(
        self, user: CurrentUser, course_id: UUID, content_type: str, file_size: int
    ) -> PresignedUpload:
        """Выдаёт форму прямой загрузки файла задания в S3.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            FileTooLargeError: файл больше лимита.
        """
        await self._editable(user, course_id)
        self._check_size(file_size)
        return await self._storage.presign_upload(
            f"{self._key_prefix(course_id)}{uuid7()}", content_type
        )

    async def create(
        self,
        user: CurrentUser,
        course_id: UUID,
        fields: AssignmentFields,
        files: Sequence[UploadedFile],
    ) -> Assignment:
        """Создаёт задание с файлами, которые браузер уже загрузил в S3.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            ForeignFileKeyError: ключ выдан не для заданий этого курса.
            FileNotUploadedError: файла в S3 нет.
            FileTooLargeError: файл больше лимита.
            FileAlreadyAttachedError: файл уже прикреплён.
        """
        async with self._storage.discard_on_error(
            [file.key for file in files],
            prefix=self._key_prefix(course_id),
            attached=self._uow.assignment_files.attached_keys,
        ):
            await self._editable(user, course_id)
            assignment = AssignmentModel(
                id=uuid7(),
                course_id=course_id,
                files=[await self._stored_file(course_id, file) for file in files],
            )
            self._apply_fields(assignment, fields)
            self._uow.assignments.add(assignment)
            await self._commit_files()
        return await self.get(user, course_id, assignment.id)

    async def get(self, user: CurrentUser, course_id: UUID, assignment_id: UUID) -> Assignment:
        """Карточка задания: студенту — его статус и оценка, преподавателю — сводка.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
            AssignmentNotFoundError: задания нет в этом курсе.
        """
        course = await self._readable(user, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        if user.role == UserRole.STUDENT:
            progress = await self._uow.submissions.progress([assignment.id], [user.user_id])
            return await self._to_dto(
                assignment,
                course,
                my_progress=GradingService.progress(progress.get((assignment.id, user.user_id))),
            )
        summaries = await self._uow.submissions.summaries(course_id, [assignment.id])
        summary = GradingService.summary(
            await self._uow.users.count_course_students(course_id), summaries.get(assignment.id)
        )
        return await self._to_dto(
            assignment,
            course,
            summary=summary,
            attempts_total=await self._uow.assignments.count_submissions(assignment.id),
        )

    async def update(
        self, user: CurrentUser, course_id: UUID, assignment_id: UUID, fields: AssignmentFields
    ) -> Assignment:
        """Меняет задание. Если по нему уже есть попытки, шкалу менять нельзя.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            ScaleLockedError: шкала меняется, а попытки уже есть.
        """
        await self._editable(user, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        current_scale = (assignment.scale_type, assignment.scale_min, assignment.scale_max)
        new_scale = (
            (fields.scale.type, fields.scale.min, fields.scale.max)
            if fields.scale is not None
            else (None, None, None)
        )
        if new_scale != current_scale and await self._uow.assignments.count_submissions(
            assignment.id
        ):
            raise ScaleLockedError({"assignment_id": str(assignment.id)})
        self._apply_fields(assignment, fields)
        await self._uow.commit()
        return await self.get(user, course_id, assignment.id)

    async def add_file(
        self, user: CurrentUser, course_id: UUID, assignment_id: UUID, file: UploadedFile
    ) -> Assignment:
        """Прикрепляет к заданию загруженный в S3 файл; задание считается изменённым.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            ForeignFileKeyError: ключ выдан не для заданий этого курса.
            FileNotUploadedError: файла в S3 нет.
            FileTooLargeError: файл больше лимита.
            FileAlreadyAttachedError: файл уже прикреплён.
        """
        async with self._storage.discard_on_error(
            [file.key],
            prefix=self._key_prefix(course_id),
            attached=self._uow.assignment_files.attached_keys,
        ):
            await self._editable(user, course_id)
            assignment = await self._get_assignment(course_id, assignment_id)
            stored = await self._stored_file(course_id, file)
            stored.assignment_id = assignment.id
            self._uow.assignment_files.add(stored)
            await self._uow.assignments.touch(assignment.id)
            await self._commit_files()
        return await self.get(user, course_id, assignment.id)

    async def delete_file(
        self, user: CurrentUser, course_id: UUID, assignment_id: UUID, file_id: UUID
    ) -> None:
        """Убирает файл из задания и из S3; задание считается изменённым.

        Удаление записи фиксируется только после удаления файла: если S3 не ответил,
        транзакция откатывается и файл остаётся.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            AssignmentFileNotFoundError: файла нет в этом задании.
            S3UnavailableError, S3TimeoutError, S3BadResponseError: файл удалить не удалось.
        """
        await self._editable(user, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        file = await self._uow.assignment_files.get_by_id(file_id)
        if file is None or file.assignment_id != assignment.id:
            raise AssignmentFileNotFoundError({"file_id": str(file_id)})
        await self._uow.assignment_files.delete(file)
        await self._uow.assignments.touch(assignment.id)
        await self._uow.flush()
        await self._storage.delete(file.file_key)
        await self._uow.commit()

    async def delete(self, user: CurrentUser, course_id: UUID, assignment_id: UUID) -> None:
        """Удаляет задание вместе со всеми попытками и всеми их файлами в S3.

        Удаление записей фиксируется только после удаления файлов: если S3 не ответил,
        транзакция откатывается и задание остаётся.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            S3UnavailableError, S3TimeoutError, S3BadResponseError: файлы удалить не удалось.
        """
        await self._editable(user, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        keys = await self._uow.assignments.file_keys(assignment.id)
        await self._uow.assignments.delete(assignment)
        await self._uow.flush()
        await self._storage.delete_many(keys)
        await self._uow.commit()

    async def student_rows(
        self,
        user: CurrentUser,
        course_id: UUID,
        assignment_id: UUID,
        search: StudentRowsFilter,
        page: PageRequest,
    ) -> Page[StudentRow]:
        """Студенты курса по заданию постранично: статус, текущая оценка, число попыток.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
            TeacherOnlyError: пользователь не преподаватель.
            AssignmentNotFoundError: задания нет в этом курсе.
        """
        await self._readable(user, course_id)
        if user.role != UserRole.TEACHER:
            raise TeacherOnlyError
        assignment = await self._get_assignment(course_id, assignment_id)
        students = await self._uow.submissions.page_students(
            course_id,
            StudentProgressFilter(assignment.id, search.group_id, search.status),
            page,
        )
        return students.map(
            tuple(
                StudentRow(
                    student_id=item.student_id,
                    last_name=item.last_name,
                    first_name=item.first_name,
                    middle_name=item.middle_name,
                    group_id=item.group_id,
                    group_name=item.group_name,
                    progress=GradingService.progress(item.progress),
                )
                for item in students.items
            )
        )

    async def _stored_file(self, course_id: UUID, file: UploadedFile) -> AssignmentFileModel:
        """Запись о файле задания по данным из S3; к заданию её привязывает вызывающий."""
        if not file.key.startswith(self._key_prefix(course_id)):
            raise ForeignFileKeyError({"course_id": str(course_id)})
        try:
            stored = await self._storage.stat(file.key)
        except S3ObjectNotFoundError as exc:
            raise FileNotUploadedError({"course_id": str(course_id)}) from exc
        self._check_size(stored.size)
        return AssignmentFileModel(
            id=uuid7(),
            file_key=file.key,
            file_name=file.file_name,
            file_size=stored.size,
            content_type=stored.content_type,
        )

    async def _commit_files(self) -> None:
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            await self._uow.rollback()
            if exc.constraint == "uq_assignment_files_file_key":
                raise FileAlreadyAttachedError from exc
            raise

    async def _get_assignment(self, course_id: UUID, assignment_id: UUID) -> AssignmentModel:
        assignment = await self._uow.assignments.get_with_files(assignment_id)
        if assignment is None or assignment.course_id != course_id:
            raise AssignmentNotFoundError({"assignment_id": str(assignment_id)})
        return assignment

    async def _to_dto(
        self,
        assignment: AssignmentModel,
        course: Course,
        *,
        my_progress: Progress | None = None,
        summary: Summary | None = None,
        attempts_total: int | None = None,
    ) -> Assignment:
        return Assignment(
            id=assignment.id,
            course_id=assignment.course_id,
            type=assignment.type,
            title=assignment.title,
            description=assignment.description,
            deadline_type=assignment.deadline_type,
            deadline_at=assignment.deadline_at,
            scale=GradingService.effective_scale(assignment, course),
            has_own_scale=assignment.scale_type is not None,
            grading_note=assignment.grading_note,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            files=tuple(
                [
                    AssignmentFile(
                        id=file.id,
                        file_name=file.file_name,
                        file_size=file.file_size,
                        content_type=file.content_type,
                        download_url=await self._storage.presign_download(
                            file.file_key, file.file_name
                        ),
                    )
                    for file in assignment.files
                ]
            ),
            my_progress=my_progress,
            summary=summary,
            attempts_total=attempts_total,
        )

    async def _readable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.readable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc

    async def _editable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.editable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc
        except access_exc.CourseArchivedError as exc:
            raise CourseArchivedError({"course_id": str(course_id)}) from exc

    @staticmethod
    def _apply_fields(assignment: AssignmentModel, fields: AssignmentFields) -> None:
        assignment.type = fields.type
        assignment.title = fields.title
        assignment.description = fields.description
        assignment.deadline_type = fields.deadline_type
        assignment.deadline_at = fields.deadline_at
        assignment.scale_type = fields.scale.type if fields.scale is not None else None
        assignment.scale_min = fields.scale.min if fields.scale is not None else None
        assignment.scale_max = fields.scale.max if fields.scale is not None else None
        assignment.grading_note = fields.grading_note

    @staticmethod
    def _key_prefix(course_id: UUID) -> str:
        return f"courses/{course_id}/assignment-files/"

    def _check_size(self, file_size: int) -> None:
        try:
            self._storage.check_size(file_size)
        except S3FileTooLargeError as exc:
            raise FileTooLargeError(exc.context) from exc
