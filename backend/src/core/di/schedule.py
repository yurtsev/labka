from dishka import Provider, Scope, provide

from src.api.schedule.service import ScheduleCourseService


class ScheduleProvider(Provider):
    schedule_course_service = provide(ScheduleCourseService, scope=Scope.REQUEST)
