from dataclasses import dataclass

from src.core.db.enums import StudyForm, StudyLevel


@dataclass(frozen=True)
class GroupSearch:
    """Поиск групп: часть названия без учёта регистра и необязательные фильтры."""

    query: str | None
    level: StudyLevel | None
    study_form: StudyForm | None
    admission_year: int | None
