from dishka import Provider, Scope, provide

from src.api.calendar.service import CalendarService


class CalendarProvider(Provider):
    calendar_service = provide(CalendarService, scope=Scope.REQUEST)
