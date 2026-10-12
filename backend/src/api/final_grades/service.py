from uuid import UUID, uuid7

from src.api.exc.final_grades import (
    CourseArchivedError,
    CourseForbiddenError,
    CourseNotFoundError,
    ExamNotAssignedError,
    FinalGradeNotFoundError,
    ResultKindMismatchError,
    StudentNotInCourseError,
    StudentOnlyError,
)
from src.api.final_grades.dto import FinalResult, MyGrade, StudentGrade
from src.core.access import exc as access_exc
from src.core.access.service import AccessService
from src.core.db.dto.page import Page, PageRequest
from src.core.db.enums import ExamType, UserRole
from src.core.db.models.course import Course
from src.core.db.models.final_grade import FinalGrade
from src.core.db.uow import UnitOfWork
from src.core.errors import InternalError
from src.core.security.dto import CurrentUser


class FinalGradeService:
    """Итоговые оценки по курсу: 2–5. Ставит преподаватель, студент видит свою."""

    def __init__(self, uow: UnitOfWork, access: AccessService) -> None:
        self._uow = uow
        self._access = access

    async def list_students(
        self, user: CurrentUser, course_id: UUID, group_id: UUID | None, page: PageRequest
    ) -> Page[StudentGrade]:
        """Студенты курса с итоговыми оценками постранично, с фильтром по группе.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
        """
        course = await self._owned(user, course_id)
        students = await self._uow.final_grades.page_students(course.id, group_id, page)
        return students.map(
            tuple(
                StudentGrade(
                    student_id=item.student_id,
                    last_name=item.last_name,
                    first_name=item.first_name,
                    middle_name=item.middle_name,
                    group_id=item.group_id,
                    group_name=item.group_name,
                    exam_type=item.exam_type,
                    grade=item.grade,
                    passed=item.passed,
                    graded_at=item.graded_at,
                )
                for item in students.items
            )
        )

    async def mine(self, user: CurrentUser, course_id: UUID) -> MyGrade:
        """Итоговая оценка студента по курсу; `grade=None`, пока не выставлена.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой.
            StudentOnlyError: пользователь не студент.
        """
        course = await self._readable(user, course_id)
        if user.role != UserRole.STUDENT:
            raise StudentOnlyError
        student = await self._uow.users.get_by_id(user.user_id)
        exam = None
        if student is not None and student.group_id is not None:
            exam = await self._uow.course_exams.get_for_group(course.id, student.group_id)
        final = await self._uow.final_grades.get(course.id, user.user_id)
        return MyGrade(
            exam_type=exam.exam_type if exam is not None else None,
            grade=final.grade if final is not None else None,
            passed=final.is_passed if final is not None else None,
            graded_at=final.updated_at if final is not None else None,
        )

    async def set_result(
        self, user: CurrentUser, course_id: UUID, student_id: UUID, result: FinalResult
    ) -> StudentGrade:
        """Выставляет или исправляет итоговый результат студента.

        Вид результата определяет форма контроля его группы: для зачёта — зачтено или нет,
        для дифф. зачёта и экзамена — оценка 2–5.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            StudentNotInCourseError: студента нет в группах курса.
            ExamNotAssignedError: группе не назначен зачёт или экзамен.
            ResultKindMismatchError: результат не того вида, что требует форма контроля.
        """
        course = await self._editable(user, course_id)
        student = await self._uow.users.get_course_student(course.id, student_id)
        if student is None or student.group_id is None:
            raise StudentNotInCourseError({"student_id": str(student_id)})
        exam = await self._uow.course_exams.get_for_group(course.id, student.group_id)
        if exam is None:
            raise ExamNotAssignedError({"group_id": str(student.group_id)})
        is_credit = exam.exam_type == ExamType.CREDIT
        if (result.passed is not None) != is_credit:
            raise ResultKindMismatchError({"exam_type": exam.exam_type.value})
        final = await self._uow.final_grades.get(course.id, student_id)
        if final is None:
            final = FinalGrade(
                id=uuid7(),
                course_id=course.id,
                student_id=student_id,
                grade=result.grade,
                is_passed=result.passed,
            )
            self._uow.final_grades.add(final)
        else:
            final.grade = result.grade
            final.is_passed = result.passed
        await self._uow.commit()
        return await self._row(course.id, student_id)

    async def clear_result(self, user: CurrentUser, course_id: UUID, student_id: UUID) -> None:
        """Снимает итоговый результат студента.

        Raises:
            CourseNotFoundError: курса нет.
            CourseForbiddenError: курс чужой или пользователь не преподаватель.
            CourseArchivedError: курс в архиве.
            FinalGradeNotFoundError: оценка не выставлена.
        """
        course = await self._editable(user, course_id)
        final = await self._uow.final_grades.get(course.id, student_id)
        if final is None:
            raise FinalGradeNotFoundError({"student_id": str(student_id)})
        await self._uow.final_grades.delete(final)
        await self._uow.commit()

    async def _row(self, course_id: UUID, student_id: UUID) -> StudentGrade:
        student = await self._uow.users.get_course_student(course_id, student_id)
        final = await self._uow.final_grades.get(course_id, student_id)
        if student is None or student.group is None or final is None:
            raise InternalError({"student_id": str(student_id)})
        exam = await self._uow.course_exams.get_for_group(course_id, student.group.id)
        return StudentGrade(
            student_id=student.id,
            last_name=student.last_name,
            first_name=student.first_name,
            middle_name=student.middle_name,
            group_id=student.group.id,
            group_name=student.group.name,
            exam_type=exam.exam_type if exam is not None else None,
            grade=final.grade,
            passed=final.is_passed,
            graded_at=final.updated_at,
        )

    async def _readable(self, user: CurrentUser, course_id: UUID) -> Course:
        try:
            return await self._access.readable_course(user, course_id)
        except access_exc.CourseNotFoundError as exc:
            raise CourseNotFoundError({"course_id": str(course_id)}) from exc
        except access_exc.CourseAccessDeniedError as exc:
            raise CourseForbiddenError({"course_id": str(course_id)}) from exc

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
