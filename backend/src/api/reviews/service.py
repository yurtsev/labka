from uuid import UUID, uuid7

from src.api.exc.reviews import (
    AlreadyReviewedError,
    AssignmentNotFoundError,
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    GradeOutOfScaleError,
    GradeRequiredError,
    NotLatestSubmissionError,
    NotReviewedError,
    StudentNotFoundError,
    SubmissionNotFoundError,
    TeacherOnlyError,
)
from src.api.reviews.dto import (
    AssignmentRef,
    Attempt,
    AttemptFile,
    AttemptReview,
    NamedRef,
    PersonRef,
    QueueFilter,
    QueueItem,
    ReviewCorrection,
    ReviewDecision,
    StudentAttempts,
)
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.dto.page import Page, PageRequest
from src.core.db.dto.submission import PendingFilter
from src.core.db.enums import ReviewVerdict, UserRole
from src.core.db.exc import IntegrityViolationError
from src.core.db.models.assignment import Assignment
from src.core.db.models.course import Course
from src.core.db.models.review import Review
from src.core.db.models.submission import Submission
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.grading import exc as grading_exc
from src.core.grading.dto import Grade
from src.core.grading.service import GradingService
from src.core.s3.service import S3Storage
from src.core.security.dto import CurrentUser


class ReviewService:
    """Проверка попыток преподавателем: очередь, вердикт и оценка, исправление оценки."""

    def __init__(self, uow: UnitOfWork, access: AccessService, storage: S3Storage) -> None:
        self._uow = uow
        self._access = access
        self._storage = storage

    async def queue(
        self, user: CurrentUser, search: QueueFilter, page: PageRequest
    ) -> Page[QueueItem]:
        """Очередь на проверку: последние непроверенные попытки по неархивным курсам
        преподавателя, старые первыми.

        Raises:
            TeacherOnlyError: пользователь не преподаватель.
        """
        if user.role != UserRole.TEACHER:
            raise TeacherOnlyError
        submissions = await self._uow.submissions.page_pending(
            PendingFilter(
                teacher_id=user.user_id,
                course_id=search.course_id,
                assignment_id=search.assignment_id,
            ),
            page,
        )
        return submissions.map(tuple(self._queue_item(item) for item in submissions.items))

    async def student_attempts(
        self, user: CurrentUser, course_id: UUID, assignment_id: UUID, student_id: UUID
    ) -> StudentAttempts:
        """Попытки студента по заданию для проверки; в архивном курсе — для просмотра.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            AssignmentNotFoundError: задания нет в этом курсе.
            StudentNotFoundError: студента нет.
        """
        course = await self._owned(user, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        student = await self._uow.users.get_by_id(student_id)
        if student is None or student.role != UserRole.STUDENT:
            raise StudentNotFoundError({"student_id": str(student_id)})
        history = await self._uow.submissions.history(assignment.id, student.id)
        return StudentAttempts(
            student=PersonRef(
                id=student.id,
                last_name=student.last_name,
                first_name=student.first_name,
                middle_name=student.middle_name,
            ),
            assignment=AssignmentRef(
                id=assignment.id, type=assignment.type, title=assignment.title
            ),
            scale=GradingService.effective_scale(assignment, course),
            attempts=tuple([await self._to_dto(item) for item in history]),
        )

    async def review(
        self,
        user: CurrentUser,
        course_id: UUID,
        assignment_id: UUID,
        submission_id: UUID,
        decision: ReviewDecision,
    ) -> Attempt:
        """Проверяет последнюю попытку студента.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            SubmissionNotFoundError: попытки нет в этом задании.
            AlreadyReviewedError: попытка уже проверена.
            NotLatestSubmissionError: у студента есть более новая попытка.
            GradeRequiredError: «принято» без оценки.
            GradeOutOfScaleError: оценка не по шкале задания.
        """
        course = await self._editable(user, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        submission = await self._get_submission(assignment, submission_id)
        if submission.review is not None:
            raise AlreadyReviewedError({"submission_id": str(submission.id)})
        last_number = await self._uow.submissions.last_number(assignment.id, submission.student_id)
        if submission.number != last_number:
            raise NotLatestSubmissionError({"submission_id": str(submission.id)})
        self._check_grade(assignment, course, decision.verdict, decision.grade)
        self._uow.reviews.add(
            Review(
                id=uuid7(),
                submission_id=submission.id,
                verdict=decision.verdict,
                score=decision.grade.score,
                is_passed=decision.grade.passed,
                comment=decision.comment,
            )
        )
        try:
            await self._uow.commit()
        except IntegrityViolationError as exc:
            if exc.constraint == "uq_reviews_submission_id":
                raise AlreadyReviewedError({"submission_id": str(submission.id)}) from exc
            raise
        return await self._reload(submission.id)

    async def correct(
        self,
        user: CurrentUser,
        course_id: UUID,
        assignment_id: UUID,
        submission_id: UUID,
        correction: ReviewCorrection,
    ) -> Attempt:
        """Исправляет оценку и комментарий уже проверенной попытки; вердикт не меняется.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            AssignmentNotFoundError: задания нет в этом курсе.
            SubmissionNotFoundError: попытки нет в этом задании.
            NotReviewedError: попытка ещё не проверена.
            GradeRequiredError: у «принято» убрали оценку.
            GradeOutOfScaleError: оценка не по шкале задания.
        """
        course = await self._editable(user, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        submission = await self._get_submission(assignment, submission_id)
        review = submission.review
        if review is None:
            raise NotReviewedError({"submission_id": str(submission.id)})
        self._check_grade(assignment, course, review.verdict, correction.grade)
        review.score = correction.grade.score
        review.is_passed = correction.grade.passed
        review.comment = correction.comment
        await self._uow.commit()
        return await self._reload(submission.id)

    async def _get_assignment(self, course_id: UUID, assignment_id: UUID) -> Assignment:
        assignment = await self._uow.assignments.get_by_id(assignment_id)
        if assignment is None or assignment.course_id != course_id:
            raise AssignmentNotFoundError({"assignment_id": str(assignment_id)})
        return assignment

    async def _get_submission(self, assignment: Assignment, submission_id: UUID) -> Submission:
        submission = await self._uow.submissions.get_with_review(submission_id)
        if submission is None or submission.assignment_id != assignment.id:
            raise SubmissionNotFoundError({"submission_id": str(submission_id)})
        return submission

    async def _reload(self, submission_id: UUID) -> Attempt:
        submission = await self._uow.submissions.get_with_review(submission_id)
        if submission is None:
            raise InternalError({"submission_id": str(submission_id)})
        return await self._to_dto(submission)

    @staticmethod
    def _check_grade(
        assignment: Assignment, course: Course, verdict: ReviewVerdict, grade: Grade
    ) -> None:
        scale = GradingService.effective_scale(assignment, course)
        try:
            GradingService.check_grade(scale, verdict, grade)
        except grading_exc.GradeRequiredError as exc:
            raise GradeRequiredError from exc
        except grading_exc.GradeOutOfScaleError as exc:
            raise GradeOutOfScaleError(exc.context) from exc

    @staticmethod
    def _queue_item(submission: Submission) -> QueueItem:
        student = submission.student
        if student.group is None:
            raise InternalError({"student_id": str(student.id)})
        assignment = submission.assignment
        return QueueItem(
            submission_id=submission.id,
            number=submission.number,
            created_at=submission.created_at,
            is_late=submission.is_late,
            student=PersonRef(
                id=student.id,
                last_name=student.last_name,
                first_name=student.first_name,
                middle_name=student.middle_name,
            ),
            group=NamedRef(id=student.group.id, name=student.group.name),
            course=NamedRef(id=assignment.course.id, name=assignment.course.name),
            assignment=AssignmentRef(
                id=assignment.id, type=assignment.type, title=assignment.title
            ),
        )

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

    async def _owned(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.owned_course(user, course_id)
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
