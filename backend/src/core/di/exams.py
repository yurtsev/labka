from dishka import Provider, Scope, provide

from src.api.exams.service import ExamService


class ExamsProvider(Provider):
    exam_service = provide(ExamService, scope=Scope.REQUEST)
