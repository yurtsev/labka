from dishka import Provider, Scope, provide

from src.core.scheduler.service import SchedulerService


class SchedulerProvider(Provider):
    scheduler_service = provide(SchedulerService, scope=Scope.APP)
