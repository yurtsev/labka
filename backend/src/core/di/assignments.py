from dishka import Provider, Scope, provide

from src.api.assignments.service import AssignmentService


class AssignmentsProvider(Provider):
    assignment_service = provide(AssignmentService, scope=Scope.REQUEST)
