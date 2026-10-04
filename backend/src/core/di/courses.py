from dishka import Provider, Scope, provide

from src.api.courses.service import CourseService


class CoursesProvider(Provider):
    course_service = provide(CourseService, scope=Scope.REQUEST)
