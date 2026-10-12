from dishka import Provider, Scope, provide

from src.api.submissions.service import SubmissionService


class SubmissionsProvider(Provider):
    submission_service = provide(SubmissionService, scope=Scope.REQUEST)
