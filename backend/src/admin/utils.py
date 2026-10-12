from uuid import UUID

from starlette.requests import Request


def normalize_email(value: str | None) -> str | None:
    """Фильтр поля формы: почта хранится в нижнем регистре и без пробелов по краям."""
    return value.strip().lower() if value else value


def selected_ids(request: Request) -> list[UUID]:
    """Выбранные в списке записи — параметр `pks` действия sqladmin; неверные id отбрасываются."""
    found = []
    for raw in request.query_params.get("pks", "").split(","):
        try:
            found.append(UUID(raw.strip()))
        except ValueError:
            continue
    return found
