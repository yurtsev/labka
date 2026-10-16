"""Тестовые данные для локальной разработки: структура вуза, пользователи, курсы и работы.

Запуск: `make seed` (наполнить пустую базу) или `make seed-reset` (очистить и наполнить заново).
Даты считаются от сегодняшнего дня: дедлайны, попытки и занятия всегда выглядят свежими.
У всех пользователей пароль `labka2026`.
"""

import argparse
import asyncio
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid7
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text

from src.core.db.db import Session, engine
from src.core.db.enums import (
    AssignmentType,
    DeadlineType,
    ExamType,
    FacultyType,
    LessonType,
    ReviewVerdict,
    ScaleType,
    ScheduleRepeat,
    SemesterTerm,
    StudyForm,
    StudyLevel,
    UserRole,
)
from src.core.db.models import (
    Announcement,
    Assignment,
    Base,
    Course,
    CourseExam,
    CourseGroup,
    CourseMaterial,
    Department,
    Direction,
    ExtraLesson,
    Faculty,
    Group,
    GroupInvite,
    PersonalTask,
    Review,
    ScheduleRule,
    Submission,
    TeacherGroup,
    User,
)
from src.core.schedule.service import ScheduleService
from src.core.security.service import SecurityService

PASSWORD = "labka2026"
MSK = ZoneInfo("Europe/Moscow")

security = SecurityService()
password_hash = security.hash_password(PASSWORD)
now = datetime.now(UTC)
today = now.astimezone(MSK).date()
semester = ScheduleService.current_semester(today)
previous = ScheduleService.semester(
    SemesterTerm.SPRING if semester.term == SemesterTerm.AUTUMN else SemesterTerm.AUTUMN,
    semester.year if semester.term == SemesterTerm.AUTUMN else semester.year - 1,
)


def ago(days: float = 0, hours: float = 0) -> datetime:
    return now - timedelta(days=days, hours=hours)


def deadline(days: int) -> datetime:
    """Дедлайн в 23:59 по МСК через `days` дней (отрицательные — в прошлом)."""
    return datetime.combine(today + timedelta(days=days), time(23, 59), MSK).astimezone(UTC)


def slot(number: int) -> tuple[time, time]:
    window = ScheduleService.slot(number)
    return window.starts_at, window.ends_at


def weekday_after(day: date, weekday: int) -> date:
    """Ближайший день недели (ISO, 1 = пн) строго после `day`."""
    return day + timedelta(days=(weekday - day.isoweekday() - 1) % 7 + 1)


class Seeder:
    def __init__(self) -> None:
        self.rows: list[Base] = []
        self.groups: dict[str, Group] = {}
        self.users: dict[str, User] = {}

    def add[T: Base](self, row: T) -> T:
        self.rows.append(row)
        return row

    # --- Структура и люди ---

    def structure(self) -> None:
        fit = self.add(
            Faculty(
                id=uuid7(),
                name="Факультет информационных технологий",
                short_name="ФИТ",
                type=FacultyType.FACULTY,
            )
        )
        self.departments = {
            "se": self.add(
                Department(id=uuid7(), faculty_id=fit.id, name="Кафедра программной инженерии")
            ),
            "math": self.add(
                Department(id=uuid7(), faculty_id=fit.id, name="Кафедра высшей математики")
            ),
            "cs": self.add(
                Department(id=uuid7(), faculty_id=fit.id, name="Кафедра вычислительной техники")
            ),
        }
        directions = {
            "ВТ": self.add(
                Direction(
                    id=uuid7(),
                    faculty_id=fit.id,
                    short_name="ВТ",
                    name="Информатика и вычислительная техника",
                )
            ),
            "ПИ": self.add(
                Direction(
                    id=uuid7(), faculty_id=fit.id, short_name="ПИ", name="Программная инженерия"
                )
            ),
        }
        for short_name, year, number in [("ПИ", 2024, 2)]:
            level = StudyLevel.BACHELOR
            name = f"{level.letter}{short_name}{year % 100:02d}{number:02d}"
            self.groups[name] = self.add(
                Group(
                    id=uuid7(),
                    direction_id=directions[short_name].id,
                    level=level,
                    study_form=StudyForm.FULL_TIME,
                    admission_year=year,
                    number=number,
                    name=name,
                    registration_code_hash=security.hash_token(
                        security.issue_registration_code()
                    ),
                )
            )

    def user(
        self,
        email: str,
        full_name: str,
        role: UserRole,
        *,
        group: str | None = None,
        department: str | None = None,
    ) -> User:
        last_name, first_name, *rest = full_name.split()
        middle_name = rest[0] if rest else None
        user = self.add(
            User(
                id=uuid7(),
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                email=email,
                password_hash=password_hash,
                role=role,
                group_id=self.groups[group].id if group else None,
                department_id=self.departments[department].id if department else None,
            )
        )
        if group:
            # Студент «зарегистрировался» по коду группы: его почта в списке группы и занята им.
            self.add(
                GroupInvite(
                    id=uuid7(), group_id=self.groups[group].id, email=email, user_id=user.id
                )
            )
        self.users[email] = user
        return user

    def people(self) -> None:
        self.user("admin@labka.com", "Админов Админ Админович", UserRole.ADMIN)

        self.user("teacher1@labka.com", "Иванов Алексей Петрович", UserRole.TEACHER, department="se")
        self.user("teacher2@labka.com", "Смирнова Елена Викторовна", UserRole.TEACHER, department="math")
        self.user("teacher3@labka.com", "Кузнецов Дмитрий Сергеевич", UserRole.TEACHER, department="cs")

        students = {
            "БПИ2402": [
                ("student@labka.com", "Бурцев Юрий Алексеевич"),
                ("student2@labka.com", "Фролов Даниил"),
                ("student3@labka.com", "Митин Даниил Олегович"),
                ("student4@labka.com", "Митин Олег Олегович"),
                ("student5@labka.com", "Орлова Мария Игоревна"),
                ("student6@labka.com", "Волков Никита Олегович"),
            ],
        }
        for group, members in students.items():
            for email, full_name in members:
                self.user(email, full_name, UserRole.STUDENT, group=group)

        # Админ прикрепляет преподавателю группы, из них он собирает курсы.
        teaching = {
            "teacher1@labka.com": ["БПИ2402"],
            "teacher2@labka.com": ["БПИ2402"],
            "teacher3@labka.com": ["БПИ2402"],
        }
        for email, groups in teaching.items():
            for group in groups:
                self.add(
                    TeacherGroup(teacher_id=self.users[email].id, group_id=self.groups[group].id)
                )

    # --- Курсы ---

    def course(
        self,
        teacher: str,
        name: str,
        description: str,
        groups: list[str],
        scale: tuple[int, int] | None,
        *,
        grading_note: str | None = None,
        archived: bool = False,
    ) -> Course:
        term = previous if archived else semester
        course = self.add(
            Course(
                id=uuid7(),
                teacher_id=self.users[teacher].id,
                name=name,
                description=description,
                term=term.term,
                year=term.year,
                scale_type=ScaleType.RANGE if scale else ScaleType.BINARY,
                scale_min=scale[0] if scale else None,
                scale_max=scale[1] if scale else None,
                grading_note=grading_note,
                is_archived=archived,
            )
        )
        for group in groups:
            self.add(CourseGroup(course_id=course.id, group_id=self.groups[group].id))
        return course

    def rule(
        self,
        course: Course,
        group: str,
        lesson_type: LessonType,
        weekday: int,
        slot_number: int,
        room: str,
        repeat: ScheduleRepeat = ScheduleRepeat.WEEKLY,
    ) -> None:
        starts_at, ends_at = slot(slot_number)
        self.add(
            ScheduleRule(
                id=uuid7(),
                course_id=course.id,
                group_id=self.groups[group].id,
                lesson_type=lesson_type,
                weekday=weekday,
                starts_at=starts_at,
                ends_at=ends_at,
                repeat=repeat,
                room=room,
            )
        )

    def exam(
        self, course: Course, group: str, exam_type: ExamType, day: date, slot_number: int, room: str
    ) -> None:
        starts_at, ends_at = slot(slot_number)
        self.add(
            CourseExam(
                id=uuid7(),
                course_id=course.id,
                group_id=self.groups[group].id,
                exam_type=exam_type,
                day=day,
                starts_at=starts_at,
                ends_at=ends_at,
                room=room,
            )
        )

    def assignment(
        self,
        course: Course,
        assignment_type: AssignmentType,
        title: str,
        description: str,
        due: datetime | None,
        *,
        hard: bool = False,
        scale: tuple[int, int] | None = None,
        binary: bool = False,
        created: datetime | None = None,
    ) -> Assignment:
        if binary:
            scale_type: ScaleType | None = ScaleType.BINARY
        elif scale:
            scale_type = ScaleType.RANGE
        else:
            scale_type = None
        return self.add(
            Assignment(
                id=uuid7(),
                course_id=course.id,
                type=assignment_type,
                title=title,
                description=description,
                deadline_type=(
                    DeadlineType.NONE if due is None else DeadlineType.HARD if hard else DeadlineType.SOFT
                ),
                deadline_at=due,
                scale_type=scale_type,
                scale_min=scale[0] if scale else None,
                scale_max=scale[1] if scale else None,
                created_at=created or ago(days=30),
            )
        )

    def submit(
        self,
        assignment: Assignment,
        student: str,
        at: datetime,
        comment: str,
        *,
        number: int = 1,
        verdict: ReviewVerdict | None = None,
        score: int | None = None,
        passed: bool | None = None,
        review: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> None:
        submission = self.add(
            Submission(
                id=uuid7(),
                assignment_id=assignment.id,
                student_id=self.users[student].id,
                number=number,
                comment=comment,
                is_late=assignment.deadline_at is not None and at > assignment.deadline_at,
                created_at=at,
            )
        )
        if verdict is not None:
            reviewed = reviewed_at or at + timedelta(days=1)
            self.add(
                Review(
                    id=uuid7(),
                    submission_id=submission.id,
                    verdict=verdict,
                    score=score,
                    is_passed=passed,
                    comment=review,
                    created_at=reviewed,
                    updated_at=reviewed,
                )
            )

    def announce(self, course: Course, at: datetime, body: str) -> None:
        self.add(Announcement(id=uuid7(), course_id=course.id, text=body, created_at=at, updated_at=at))

    def material(self, course: Course, at: datetime, title: str, body: str) -> None:
        self.add(
            CourseMaterial(
                id=uuid7(), course_id=course.id, title=title, text=body, created_at=at, updated_at=at
            )
        )

    def courses(self) -> None:
        session_day = semester.classes_end_on + timedelta(days=12)

        # Иванов: «Базы данных» — главный курс с полным набором состояний работ.
        db = self.course(
            "teacher1@labka.com",
            "Базы данных",
            "Реляционная модель, SQL, проектирование схем, транзакции и индексы. "
            "Практика на PostgreSQL.",
            ["БПИ2402"],
            (0, 100),
            grading_note="Итог — сумма баллов за лабораторные. Допуск к экзамену от 60 баллов.",
        )
        self.rule(db, "БПИ2402", LessonType.LAB, 1, 2, "А-305")
        self.rule(db, "БПИ2402", LessonType.PRACTICE, 3, 3, "А-212", ScheduleRepeat.EVEN)
        self.exam(db, "БПИ2402", ExamType.EXAM, session_day, 2, "А-101")
        self.add(
            ExtraLesson(
                id=uuid7(),
                course_id=db.id,
                group_id=self.groups["БПИ2402"].id,
                lesson_type=LessonType.LAB,
                day=weekday_after(today, 6),
                starts_at=slot(3)[0],
                ends_at=slot(3)[1],
                room="А-305",
            )
        )

        db_lab1 = self.assignment(
            db,
            AssignmentType.LAB,
            "ЛР 1. Проектирование схемы",
            "Спроектируйте схему БД библиотеки: ER-диаграмма и DDL-скрипт. "
            "Приложите скрипт и короткое пояснение к связям.",
            deadline(-25),
            scale=(0, 20),
            created=ago(days=40),
        )
        db_lab2 = self.assignment(
            db,
            AssignmentType.LAB,
            "ЛР 2. Запросы SELECT и JOIN",
            "Напишите 15 запросов к схеме из ЛР 1: выборки, соединения, группировки.",
            deadline(-10),
            scale=(0, 20),
            created=ago(days=28),
        )
        db_lab3 = self.assignment(
            db,
            AssignmentType.LAB,
            "ЛР 3. Индексы и EXPLAIN",
            "Сравните планы запросов до и после индексов. Отчёт — таблица времени и выводы.",
            datetime.combine(today + timedelta(days=1), time(12, 0), MSK).astimezone(UTC),
            hard=True,
            scale=(0, 25),
            created=ago(days=12),
        )
        self.assignment(
            db,
            AssignmentType.LAB,
            "ЛР 4. Транзакции и блокировки",
            "Воспроизведите аномалии изоляции и покажите, какой уровень их убирает.",
            deadline(14),
            scale=(0, 35),
            created=ago(days=2),
        )
        db_hw = self.assignment(
            db,
            AssignmentType.HW,
            "ДЗ. Нормализация",
            "Приведите таблицы из методички к 3НФ, покажите каждый шаг.",
            None,
            binary=True,
            created=ago(days=20),
        )

        me = "student@labka.com"
        self.submit(
            db_lab1, me, ago(days=27), "Схема и DDL во вложении, связи описал в README.",
            verdict=ReviewVerdict.ACCEPTED, score=18, review="Хорошо. Не хватает индекса на FK.",
        )
        self.submit(
            db_lab2, me, ago(days=12), "Первая версия, запросы 1–15.",
            verdict=ReviewVerdict.REVISION, review="Запросы 7 и 12 возвращают дубли — нужен DISTINCT или GROUP BY.",
        )
        self.submit(db_lab2, me, ago(days=8), "Исправил 7 и 12.", number=2)
        self.submit(
            db_hw, me, ago(days=15), "Разобрал все три таблицы.",
            verdict=ReviewVerdict.ACCEPTED, passed=True,
        )
        self.submit(
            db_lab1, "student2@labka.com", ago(days=26), "Готово.",
            verdict=ReviewVerdict.ACCEPTED, score=20, review="Отлично.",
        )
        self.submit(db_lab1, "student3@labka.com", ago(days=21), "Сдаю с опозданием, болел.")
        self.submit(db_lab2, "student2@labka.com", ago(days=11), "Все запросы в одном файле.")
        self.submit(db_lab2, "student4@labka.com", ago(days=10, hours=3), "Сделала 14 из 15.")
        self.submit(db_lab3, "student2@labka.com", ago(hours=5), "Отчёт с графиками.")
        self.submit(db_lab1, "student5@labka.com", ago(days=26), "ER-диаграмма и скрипт.")

        self.announce(db, ago(days=35), "Добро пожаловать на курс! Методички — в разделе материалов.")
        self.announce(db, ago(days=3), "Срок ЛР 3 жёсткий: после дедлайна сдать не получится.")
        self.material(
            db,
            ago(days=38),
            "Программа курса",
            "## Темы\n\n1. Реляционная модель\n2. SQL: DDL и DML\n3. Индексы\n4. Транзакции\n\n"
            "Документация PostgreSQL: https://www.postgresql.org/docs/",
        )
        self.material(
            db,
            ago(days=14),
            "Лекция 5. Индексы",
            "B-tree, hash, GIN. Когда индекс не помогает. Разбор `EXPLAIN ANALYZE`.",
        )

        # Иванов: «Веб-разработка».
        web = self.course(
            "teacher1@labka.com",
            "Веб-разработка",
            "HTTP, HTML/CSS, основы React и REST API.",
            ["БПИ2402"],
            (0, 10),
        )
        self.rule(web, "БПИ2402", LessonType.LAB, 4, 3, "Б-110")
        self.assignment(
            web, AssignmentType.LAB, "Вёрстка лендинга", "Сверстайте макет из Figma.", deadline(5),
            created=ago(days=6),
        )

        # Смирнова: «Математический анализ» — общий для двух групп.
        calc = self.course(
            "teacher2@labka.com",
            "Математический анализ",
            "Пределы, производные, интегралы, ряды.",
            ["БПИ2402"],
            (2, 5),
            grading_note="Оценка за каждое ДЗ — от 2 до 5.",
        )
        self.rule(calc, "БПИ2402", LessonType.PRACTICE, 2, 2, "В-401")
        self.rule(calc, "БПИ2402", LessonType.PRACTICE, 4, 1, "В-401", ScheduleRepeat.ODD)
        self.exam(calc, "БПИ2402", ExamType.EXAM, session_day + timedelta(days=5), 1, "В-401")
        calc_hw1 = self.assignment(
            calc, AssignmentType.HW, "ДЗ 1. Пределы", "Задачи 1.1–1.20 из задачника.", deadline(-18),
            created=ago(days=30),
        )
        calc_hw2 = self.assignment(
            calc, AssignmentType.HW, "ДЗ 2. Производные", "Задачи 2.1–2.25.", deadline(-2),
            created=ago(days=16),
        )
        self.assignment(
            calc, AssignmentType.HW, "ДЗ 3. Интегралы", "Задачи 3.1–3.30.", deadline(9),
            created=ago(days=1),
        )
        self.submit(
            calc_hw1, me, ago(days=20), "Решения сфотографированы.",
            verdict=ReviewVerdict.ACCEPTED, score=4, review="В 1.17 ошибка в знаке.",
        )
        self.submit(calc_hw2, me, ago(days=1), "Извините, сдаю с опозданием.")
        self.submit(
            calc_hw1, "student3@labka.com", ago(days=19), "Готово.",
            verdict=ReviewVerdict.ACCEPTED, score=5,
        )
        self.announce(calc, ago(days=6), "Контрольная по производным — в следующую среду.")
        self.material(calc, ago(days=25), "Таблица производных", "| f(x) | f'(x) |\n|---|---|\n| xⁿ | n·xⁿ⁻¹ |\n| sin x | cos x |\n| eˣ | eˣ |")

        # Смирнова: «Дискретная математика».
        discrete = self.course(
            "teacher2@labka.com",
            "Дискретная математика",
            "Множества, графы, комбинаторика.",
            ["БПИ2402"],
            None,
        )
        self.rule(discrete, "БПИ2402", LessonType.PRACTICE, 1, 4, "В-402")
        self.exam(discrete, "БПИ2402", ExamType.CREDIT, semester.classes_end_on - timedelta(days=3), 3, "В-402")

        # Кузнецов: «Операционные системы» — зачёт/незачёт.
        os_course = self.course(
            "teacher3@labka.com",
            "Операционные системы",
            "Процессы, потоки, память, файловые системы. Лабораторные на C под Linux.",
            ["БПИ2402"],
            None,
            grading_note="Зачёт — все лабораторные приняты.",
        )
        self.rule(os_course, "БПИ2402", LessonType.LAB, 5, 3, "Г-15", ScheduleRepeat.EVEN)
        self.exam(os_course, "БПИ2402", ExamType.CREDIT, semester.classes_end_on - timedelta(days=2), 2, "Г-15")
        os_lab1 = self.assignment(
            os_course, AssignmentType.LAB, "ЛР 1. fork и exec", "Напишите мини-оболочку.", deadline(-14),
            hard=True, created=ago(days=30),
        )
        self.assignment(
            os_course, AssignmentType.LAB, "ЛР 2. Потоки и мьютексы", "Производитель–потребитель на pthreads.",
            deadline(3), created=ago(days=10),
        )
        self.assignment(
            os_course, AssignmentType.PRACTICE, "Практика. Права доступа", "Разберите вывод `ls -l` и `chmod`.",
            None, created=ago(days=4),
        )
        self.submit(
            os_lab1, me, ago(days=16), "Оболочка поддерживает пайпы.",
            verdict=ReviewVerdict.ACCEPTED, passed=True, review="Зачтено.",
        )
        self.submit(
            os_lab1, "student4@labka.com", ago(days=15), "Без пайпов пока.",
            verdict=ReviewVerdict.REVISION, review="Добавьте пайпы.",
        )
        self.announce(os_course, ago(days=9), "Лабораторные сдаём только через систему, по почте не принимаю.")
        self.material(os_course, ago(days=29), "Как собрать стенд", "```sh\nsudo apt install build-essential gdb\n```")

        # Кузнецов: прошлый семестр, курс в архиве.
        algo = self.course(
            "teacher3@labka.com",
            "Алгоритмы и структуры данных",
            "Сортировки, деревья, графы, динамическое программирование.",
            ["БПИ2402"],
            (0, 100),
            archived=True,
        )
        algo_lab = self.assignment(
            algo, AssignmentType.LAB, "Курсовая. Дерево отрезков", "Реализация и тесты.",
            datetime.combine(previous.classes_end_on, time(23, 59), MSK).astimezone(UTC),
            created=datetime.combine(previous.starts_on, time(10, 0), MSK).astimezone(UTC),
        )
        self.submit(
            algo_lab, me,
            datetime.combine(previous.classes_end_on - timedelta(days=5), time(18, 0), MSK).astimezone(UTC),
            "Курсовая во вложении.",
            verdict=ReviewVerdict.ACCEPTED, score=87,
        )


    def personal(self) -> None:
        student = self.users["student@labka.com"].id
        for days, at, title, done in [
            (-1, time(19, 0), "Купить тетрадь для матана", True),
            (0, None, "Повторить JOIN перед ЛР 3", False),
            (2, time(10, 0), "Записаться в библиотеку", False),
            (6, None, "Подготовиться к контрольной по производным", False),
        ]:
            self.add(
                PersonalTask(
                    id=uuid7(),
                    student_id=student,
                    title=title,
                    due_date=today + timedelta(days=days),
                    due_time=at,
                    is_done=done,
                )
            )


async def reset() -> None:
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


async def main(force_reset: bool) -> None:
    async with Session() as session:
        users = await session.scalar(select(func.count()).select_from(User))
    if users and not force_reset:
        raise SystemExit(f"В базе уже {users} пользователей. Очистить и наполнить заново: make seed-reset")
    if force_reset:
        await reset()

    seeder = Seeder()
    seeder.structure()
    seeder.people()
    seeder.courses()
    seeder.personal()

    async with Session() as session:
        # Без relationship ORM не знает порядок таблиц: вставляем по их внешним ключам.
        for table in Base.metadata.sorted_tables:
            session.add_all(row for row in seeder.rows if row.__table__ is table)
            await session.flush()
        await session.commit()
    await engine.dispose()

    print(f"Готово: {len(seeder.rows)} записей. Семестр: {semester.term} {semester.year}.")
    print(f"Пароль у всех: {PASSWORD}")
    for email, user in seeder.users.items():
        if user.role != UserRole.STUDENT or email == "student@labka.com":
            print(f"  {user.role:<8} {email}")
    print("  student  student2…student6@labka.com — одногруппники из БПИ2402")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="очистить все таблицы перед наполнением")
    asyncio.run(main(parser.parse_args().reset))
