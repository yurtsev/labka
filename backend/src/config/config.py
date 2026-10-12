from datetime import time
from pathlib import Path
from urllib.parse import quote

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

BASE_DIR = Path(__file__).parent.parent.parent
TOML_SETTINGS_PATH = BASE_DIR / "config.toml"

PathsSources: list[tuple[Path, type[PydanticBaseSettingsSource]]] = [
    (TOML_SETTINGS_PATH, TomlConfigSettingsSource),
]


class CORS(BaseModel):
    origins: list[str] = []


class Database(BaseModel):
    postgres_username: str = ""
    postgres_db: str = ""
    postgres_port: int = 5432
    postgres_host: str = ""
    postgres_password: str = ""

    alembic_postgres_host: str | None = None

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def asyncpg_dsn(self) -> str:
        """Адрес для прямого соединения asyncpg (LISTEN вне пула SQLAlchemy)."""
        user, password = (
            quote(self.postgres_username, safe=""),
            quote(self.postgres_password, safe=""),
        )
        return f"postgresql://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def alembic_url(self) -> str:
        host = self.alembic_postgres_host or self.postgres_host
        return f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}@{host}:{self.postgres_port}/{self.postgres_db}"


class Auth(BaseModel):
    jwt_secret: str = ""
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    admin_session_ttl_hours: int = 12
    cookie_secure: bool = True
    password_min_length: int = 8
    password_max_length: int = 32


class S3(BaseModel):
    # Адрес, по которому S3 доступен бэкенду (в Docker — имя сервиса).
    endpoint_url: str = ""
    # Адрес для браузера: на него выписываются presigned-ссылки. Пусто — как endpoint_url.
    public_endpoint_url: str = ""
    region: str = "us-east-1"
    access_key: str = ""
    secret_key: str = ""
    bucket: str = ""
    max_file_size_bytes: int = 20 * 1024 * 1024
    url_ttl_seconds: int = 900
    timeout_seconds: float = 10


class Pagination(BaseModel):
    default_per_page: int = 20
    max_per_page: int = 100


class MonthDay(BaseModel):
    month: int
    day: int


class LessonSlot(BaseModel):
    """Окно пары: занятия ставятся только на такие окна."""

    number: int
    starts_at: time
    ends_at: time


class Schedule(BaseModel):
    slots: list[LessonSlot] = [
        LessonSlot(number=1, starts_at=time(9, 30), ends_at=time(11, 0)),
        LessonSlot(number=2, starts_at=time(11, 15), ends_at=time(12, 45)),
        LessonSlot(number=3, starts_at=time(13, 0), ends_at=time(14, 30)),
        LessonSlot(number=4, starts_at=time(15, 10), ends_at=time(16, 40)),
        LessonSlot(number=5, starts_at=time(16, 55), ends_at=time(18, 25)),
    ]
    # Осенний (нечётный) семестр: пары до `autumn_classes_end`, дальше только сессия.
    autumn_starts: MonthDay = MonthDay(month=9, day=1)
    autumn_classes_end: MonthDay = MonthDay(month=12, day=30)
    autumn_ends: MonthDay = MonthDay(month=1, day=31)
    # Весенний (чётный) семестр.
    spring_starts: MonthDay = MonthDay(month=2, day=1)
    spring_classes_end: MonthDay = MonthDay(month=7, day=10)
    spring_ends: MonthDay = MonthDay(month=7, day=10)
    # Самый длинный период личных задач в одном запросе.
    personal_tasks_max_range_days: int = 366


class Notifications(BaseModel):
    # За сколько часов до дедлайна напоминать и как часто проверять задания.
    reminder_window_hours: int = 24
    reminder_interval_minutes: int = 5
    # Как часто WebSocket спрашивает «ты здесь?» и сколько ждёт ответа.
    websocket_ping_seconds: int = 30


class Dashboard(BaseModel):
    # Сколько ближайших занятий и дедлайнов и карточек курсов показывает главная.
    upcoming_lessons: int = 3
    upcoming_deadlines: int = 3
    courses: int = 12
    # На сколько дней вперёд искать ближайшие занятия.
    lessons_horizon_days: int = 60


class Administration(BaseModel):
    # Сколько групп можно создать за раз.
    max_batch_groups: int = 30


class Logging(BaseModel):
    level: str = "INFO"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        toml_file=TOML_SETTINGS_PATH,
        env_nested_delimiter="__",
    )

    database: Database = Database()
    logging: Logging = Logging()
    cors: CORS = CORS()
    auth: Auth = Auth()
    pagination: Pagination = Pagination()
    s3: S3 = S3()
    schedule: Schedule = Schedule()
    notifications: Notifications = Notifications()
    dashboard: Dashboard = Dashboard()
    administration: Administration = Administration()

    def missing_required(self) -> list[str]:
        """Настройки, без которых приложение не запускается, но которые не заданы."""
        required = {
            "database.postgres_host": self.database.postgres_host,
            "database.postgres_db": self.database.postgres_db,
            "database.postgres_username": self.database.postgres_username,
            "auth.jwt_secret": self.auth.jwt_secret,
            "s3.endpoint_url": self.s3.endpoint_url,
            "s3.bucket": self.s3.bucket,
            "s3.access_key": self.s3.access_key,
            "s3.secret_key": self.s3.secret_key,
        }
        return [name for name, value in required.items() if not value]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        active_sources = [method(settings_cls) for path, method in PathsSources if path.exists()]
        return EnvSettingsSource(settings_cls), *active_sources


cfg = Config()
