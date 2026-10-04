import enum
import re
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, MetaData, inspect
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    # Enum'ы хранятся как VARCHAR + CHECK по значениям: нативный PG ENUM неудобно расширять.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        enum.Enum: Enum(
            enum.Enum,
            native_enum=False,
            create_constraint=True,
            length=32,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
    }
    # Серверные значения (created_at, updated_at, флаги) подгружаются через RETURNING,
    # иначе обращение к ним после flush в async-сессии запустит ленивую загрузку.
    __mapper_args__: Any = {"eager_defaults": True}

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Имя таблицы — snake_case во множественном числе: `GroupInvite` → `group_invites`."""
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        if snake.endswith("y"):
            return f"{snake[:-1]}ies"
        if snake.endswith(("s", "x", "ch", "sh")):
            return f"{snake}es"
        return f"{snake}s"

    def to_dict(self) -> dict[str, object]:
        """Преобразует объект модели в словарь по колонкам."""
        mapper = inspect(self.__class__)
        columns = getattr(mapper, "columns", None)
        if columns is None:
            return {}

        data: dict[str, object] = {}
        for col in columns:
            data[col.key] = getattr(self, col.key)
        return data

    def update(self: Base, **kwargs: object) -> Base:
        """Обновляет существующие атрибуты объекта, неизвестные ключи пропускает."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self

    @classmethod
    def from_dict(cls: type[Base], data: dict[str, object]) -> Base:
        """Создаёт экземпляр из словаря, оставляя только ключи, совпадающие с колонками."""
        mapper = inspect(cls)
        columns = getattr(mapper, "columns", None)
        allowed = {c.key for c in columns} if columns is not None else set()

        obj = cls()
        for k, v in data.items():
            if k in allowed:
                setattr(obj, k, v)
        return obj
