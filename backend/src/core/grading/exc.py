from src.core.errors import CoreError


class GradeRequiredError(CoreError):
    code = "grading.grade_required"
    message = "При вердикте «принято» оценка обязательна"


class GradeOutOfScaleError(CoreError):
    code = "grading.grade_out_of_scale"
    message = "Оценка не соответствует шкале задания"
