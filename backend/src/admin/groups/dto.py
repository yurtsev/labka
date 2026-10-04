from dataclasses import dataclass
from uuid import UUID

from src.core.db.enums import StudyForm, StudyLevel


@dataclass(frozen=True)
class GroupFields:
    direction_id: UUID
    level: StudyLevel
    study_form: StudyForm
    admission_year: int
    number: int
    # None — собрать название автоматически: `Б` + `ВТ` + `26` + `01` = `БВТ2601`.
    name: str | None


@dataclass(frozen=True)
class CreatedGroup:
    group_id: UUID
    registration_code: str
