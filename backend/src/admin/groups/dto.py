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


@dataclass(frozen=True)
class BatchFields:
    """Группы пачкой: у всех одно направление, уровень, форма и год, номера по порядку с 1."""

    direction_id: UUID
    level: StudyLevel
    study_form: StudyForm
    admission_year: int
    count: int


@dataclass(frozen=True)
class CreatedBatchGroup:
    name: str
    registration_code: str


@dataclass(frozen=True)
class InviteImport:
    """Итог загрузки списка почт в группу."""

    added: tuple[str, ...]
    # Не похоже на почту.
    invalid: tuple[str, ...]
    # Повторы внутри самого списка.
    repeated: tuple[str, ...]
    # Уже были в списке этой или другой группы.
    already_listed: tuple[str, ...]
