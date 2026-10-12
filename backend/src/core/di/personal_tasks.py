from dishka import Provider, Scope, provide

from src.api.personal_tasks.service import PersonalTaskService


class PersonalTasksProvider(Provider):
    personal_task_service = provide(PersonalTaskService, scope=Scope.REQUEST)
