from dishka import Provider, Scope, provide

from src.api.calendar.service import CalendarService, PersonalTaskService


class CalendarProvider(Provider):
    calendar_service = provide(CalendarService, scope=Scope.REQUEST)
    personal_task_service = provide(PersonalTaskService, scope=Scope.REQUEST)
