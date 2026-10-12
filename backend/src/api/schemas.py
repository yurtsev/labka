from datetime import date

from pydantic import BaseModel

from src.core.db.enums import SemesterTerm


class SemesterResponse(BaseModel):
    """Семестр: пары идут до `classes_end_on`, до `ends_on` — только сессия."""

    term: SemesterTerm
    year: int
    starts_on: date
    classes_end_on: date
    ends_on: date
