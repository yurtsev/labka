from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid7

from src.api.exc.submissions import (
    AlreadyAcceptedError,
    AssignmentNotFoundError,
    ConcurrentSubmissionError,
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    DeadlinePassedError,
    EmptySubmissionError,
    FileAlreadyAttachedError,
    FileNotUploadedError,
    FileTooLargeError,
    ForeignFileKeyError,
    StudentOnlyError,
)
from src.api.submissions.dto import Attempt, AttemptFile, AttemptReview, Attempts, UploadedFile
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.enums import DeadlineType, ReviewVerdict, UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.assignment import Assignment
from src.core.db.models.course import Course
from src.core.db.models.submission import Submission
from src.core.db.models.submission_file import SubmissionFile
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.grading.dto import Grade
from src.core.s3.dto import PresignedUpload
from src.core.s3.exc import S3FileTooLargeError, S3ObjectNotFoundError
from src.core.s3.service import S3Storage
from src.core.security.dto import CurrentUser


class SubmissionService:
    """Сдача работ студентом: попытки с файлами и комментарием, история попыток."""

    def __init__(self, uow: UnitOfWork, access: AccessService, storage: S3Storage) -> None:
        self._uow = uow
        self._access = access
        self._storage = storage

    async def start_upload(
        self,
        user: CurrentUser,
        course_id: UUID,
        assignment_id: UUID,
        content_type: str,
        file_size: int,
    ) -> PresignedUpload:
        """Выдаёт форму прямой загрузки файла попытки в S3, если сдавать сейчас можно.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
            StudentOnlyError: пользователь не студент.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            AlreadyAcceptedError: работа уже принята.
            DeadlinePassedError: жёсткий дедлайн прошёл и пересдача не разрешена.
            FileTooLargeError: файл больше лимита.
        """
        assignment = await self._submittable_assignment(user, course_id, assignment_id)
        history = await self._uow.submissions.history(assignment.id, user.user_id)
        self._check_can_submit(assignment, history, datetime.now(UTC))
        self._check_size(file_size)
        return await self._storage.presign_upload(
            f"{self._key_prefix(course_id, assignment.id, user.user_id)}{uuid7()}", content_type
        )

    async def submit(
        self,
        user: CurrentUser,
        course_id: UUID,
        assignment_id: UUID,
        comment: str | None,
        files: Sequence[UploadedFile],
    ) -> Attempt:
        """Отправляет новую попытку; более ранняя непроверенная остаётся только в истории.

        Мягкий дедлайн прошёл — попытка отмечается просроченной. После жёсткого дедлайна
        можно только пересдать работу, возвращённую на доработку, и только если первая
        попытка была до дедлайна.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
            StudentOnlyError: пользователь не студент.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            EmptySubmissionError: нет ни файлов, ни комментария.
            AlreadyAcceptedError: работа уже принята.
            DeadlinePassedError: жёсткий дедлайн прошёл и пересдача не разрешена.
            ForeignFileKeyError: ключ выдан не для этой сдачи.
            FileNotUploadedError: файла в S3 нет.
            FileTooLargeError: файл больше лимита.
            FileAlreadyAttachedError: файл уже прикреплён.
            ConcurrentSubmissionError: параллельно отправлена другая попытка.
        """
        prefix = self._key_prefix(course_id, assignment_id, user.user_id)
        async with self._storage.discard_on_error(
            [file.key for file in files],
            prefix=prefix,
            attached=self._uow.submission_files.attached_keys,
        ):
            assignment = await self._submittable_assignment(user, course_id, assignment_id)
            if not comment and not files:
                raise EmptySubmissionError
            history = await self._uow.submissions.history(assignment.id, user.user_id)
            is_late = self._check_can_submit(assignment, history, datetime.now(UTC))
            submission = Submission(
                id=uuid7(),
                assignment_id=assignment.id,
                student_id=user.user_id,
                number=(history[0].number if history else 0) + 1,
                comment=comment,
                is_late=is_late,
                files=[await self._stored_file(prefix, file) for file in files],
            )
            self._uow.submissions.add(submission)
            try:
                await self._uow.commit()
            except IntegrityViolationError as exc:
                await self._uow.rollback()
                if exc.constraint == "uq_submissions_assignment_id_student_id_number":
                    raise ConcurrentSubmissionError from exc
                if exc.constraint == "uq_submission_files_file_key":
                    raise FileAlreadyAttachedError from exc
                raise
        saved = await self._uow.submissions.get_with_review(submission.id)
        if saved is None:
            raise InternalError({"submission_id": str(submission.id)})
        return await self._to_dto(saved)

    async def history(self, user: CurrentUser, course_id: UUID, assignment_id: UUID) -> Attempts:
        """Мои попытки по заданию с проверками, новые первыми; в архивном курсе тоже.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
            StudentOnlyError: пользователь не студент.
            AssignmentNotFoundError: задания нет в этом курсе.
        """
        await self._readable(user, course_id)
        if user.role != UserRole.STUDENT:
            raise StudentOnlyError
        assignment = await self._get_assignment(course_id, assignment_id)
        history = await self._uow.submissions.history(assignment.id, user.user_id)
        return Attempts(items=tuple([await self._to_dto(item) for item in history]))

    async def _submittable_assignment(
        self, user: CurrentUser, course_id: UUID, assignment_id: UUID
    ) -> Assignment:
        course = await self._readable(user, course_id)
        if user.role != UserRole.STUDENT:
            raise StudentOnlyError
        if course.is_archived:
            raise CourseArchivedError({"course_id": str(course_id)})
        return await self._get_assignment(course_id, assignment_id)

    @staticmethod
    def _check_can_submit(
        assignment: Assignment, history: Sequence[Submission], now: datetime
    ) -> bool:
        """Проверяет, можно ли сейчас сдать работу.

        Args:
            history: попытки студента по заданию с проверками, новые первыми.

        Returns:
            Будет ли попытка просроченной (мягкий дедлайн прошёл).
        """
        if any(item.review and item.review.verdict == ReviewVerdict.ACCEPTED for item in history):
            raise AlreadyAcceptedError({"assignment_id": str(assignment.id)})
        deadline = assignment.deadline_at
        if deadline is None or now <= deadline:
            return False
        if assignment.deadline_type == DeadlineType.HARD:
            submitted_in_time = any(item.created_at <= deadline for item in history)
            returned = (
                bool(history)
                and history[0].review is not None
                and history[0].review.verdict == ReviewVerdict.REVISION
            )
            if not (submitted_in_time and returned):
                raise DeadlinePassedError({"assignment_id": str(assignment.id)})
            return False
        return True

    async def _stored_file(self, prefix: str, file: UploadedFile) -> SubmissionFile:
        if not file.key.startswith(prefix):
            raise ForeignFileKeyError
        try:
            stored = await self._storage.stat(file.key)
        except S3ObjectNotFoundError as exc:
            raise FileNotUploadedError from exc
        self._check_size(stored.size)
        return SubmissionFile(
            id=uuid7(),
            file_key=file.key,
            file_name=file.file_name,
            file_size=stored.size,
            content_type=stored.content_type,
        )

    async def _get_assignment(self, course_id: UUID, assignment_id: UUID) -> Assignment:
        assignment = await self._uow.assignments.get_by_id(assignment_id)
        if assignment is None or assignment.course_id != course_id:
            raise AssignmentNotFoundError({"assignment_id": str(assignment_id)})
        return assignment

    async def _to_dto(self, submission: Submission) -> Attempt:
        review = submission.review
        return Attempt(
            id=submission.id,
            number=submission.number,
            comment=submission.comment,
            is_late=submission.is_late,
            created_at=submission.created_at,
            files=tuple(
                [
                    AttemptFile(
                        id=file.id,
                        file_name=file.file_name,
                        file_size=file.file_size,
                        content_type=file.content_type,
                        download_url=await self._storage.presign_download(
                            file.file_key, file.file_name
                        ),
                    )
                    for file in submission.files
                ]
            ),
            review=AttemptReview(
                verdict=review.verdict,
                grade=Grade(review.score, review.is_passed)
                if review.score is not None or review.is_passed is not None
                else None,
                comment=review.comment,
                created_at=review.created_at,
                updated_at=review.updated_at,
            )
            if review is not None
            else None,
        )

    async def _readable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.readable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc

    @staticmethod
    def _key_prefix(course_id: UUID, assignment_id: UUID, student_id: UUID) -> str:
        return f"courses/{course_id}/submissions/{assignment_id}/{student_id}/"

    def _check_size(self, file_size: int) -> None:
        try:
            self._storage.check_size(file_size)
        except S3FileTooLargeError as exc:
            raise FileTooLargeError(exc.context) from exc
