def normalize_email(value: str | None) -> str | None:
    """Фильтр поля формы: почта хранится в нижнем регистре и без пробелов по краям."""
    return value.strip().lower() if value else value
