from dishka import Provider, Scope, provide

from src.api.final_grades.service import FinalGradeService


class FinalGradesProvider(Provider):
    final_grade_service = provide(FinalGradeService, scope=Scope.REQUEST)
