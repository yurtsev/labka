# Labka — backend

FastAPI-сервис Labka: REST API на `/api`, WebSocket уведомлений на `/api/ws` и админка на `/admin`.
Что такое Labka и как поднять проект целиком, описано в [корневом README](../README.md).

## Запуск

### В Docker

Сначала нужно поднять окружение из [`../infra`](../infra/README.md): backend подключается к его
Docker-сети `labka`.

```bash
make -C ../infra up
cp config.toml.example config.toml   # заменить все change-me; учётки БД и S3 — как в infra/.env
make up                              # собрать образ, применить миграции, запустить backend
make create-admin-docker             # создать администратора
```

`make up` поднимает два контейнера: `migrate` (выполняет `alembic upgrade head` и завершается) и
`backend`, который стартует только после успешных миграций. Порт 8000 слушается только на
`127.0.0.1`.

### Без Docker

PostgreSQL и S3 всё равно нужны — проще всего взять их из `../infra`. В `config.toml` поменяйте
адреса внутри Docker-сети на локальные: `postgres_host = "localhost"`,
`s3.endpoint_url = "http://localhost:9000"`.

```bash
uv sync
make upgrade        # применить миграции
make run            # http://localhost:8000
make create-admin   # создать администратора
```

После запуска: Swagger — http://localhost:8000/docs, админка — http://localhost:8000/admin.

Приложение работает **строго в одном процессе** (uvicorn с `workers=1`): слушатель PostgreSQL,
планировщик и реестр WebSocket-соединений живут в памяти процесса.

## Команды

Полный список — `make help`.

| Команда | Что делает |
|---|---|
| `make up` / `down` / `build` / `logs` / `ps` | docker-compose backend |
| `make run` | запуск без Docker |
| `make create-admin` / `create-admin-docker` | создать администратора локально / в контейнере |
| `make upgrade` | применить миграции |
| `make downgrade REV=<rev>` | откатить до ревизии |
| `make migrate MSG="<описание>"` | создать автомиграцию |
| `make check` | ruff format --check, ruff check, mypy |
| `make lint-fix` | отформатировать и автоисправить |
| `make test` | unit-тесты, без Docker |
| `make test-integration` | integration-тесты (нужен Docker) |
| `make test-all` | все тесты |

## Структура

```
src/
├── main.py              сборка приложения: DI-контейнер, middleware, роутеры, слушатель и планировщик
├── config/              настройки (pydantic-settings), доступ через `from src.config import cfg`
├── admin/               sqladmin на /admin: структура вуза, группы, почты, преподаватели, студенты; CLI create-admin
├── api/
│   ├── <домен>/         router / schemas / service (+ dto, presenter, utils по необходимости)
│   └── exc/             ошибки доменов и единый обработчик ошибок
└── core/
    ├── db/              модели, репозитории, unit of work
    ├── di/              провайдеры dishka
    ├── errors/          базовая иерархия ошибок
    ├── access/          кто что может видеть и менять
    ├── grading/         шкалы, статусы и оценки по заданиям
    ├── schedule/        вычисление занятий из правил расписания
    ├── notifications/   создание и рендер уведомлений, напоминания о дедлайнах
    ├── realtime/        слушатель PostgreSQL NOTIFY и реестр WebSocket-соединений
    ├── scheduler/       APScheduler
    ├── s3/              клиент и presigned-ссылки
    └── security/        пароли, токены
alembic/versions/        миграции
tests/                   unit/, integration/, support/ и манифест сценариев scenarios.toml
```

API-домены: `auth`, `profile`, `home`, `courses`, `materials`, `announcements`, `assignments`,
`submissions`, `reviews`, `feed`, `schedule`, `calendar` (включая личные задачи), `exams`,
`notifications`.

### Правила слоёв

- Запрос идёт router → service → unit of work / репозитории → модели, зависимости — только вниз.
- API-домены не импортируют друг друга. Общее выносится в `core`.
- `core` не импортирует `api` — исключение только провайдеры в `core/di`.
- Импорты абсолютные от корня `backend/`: `from src.core.db.uow import UnitOfWork`.

Правило про импорты проверяется тестом (`ARCH-IMPORTS-001`).

## Конфигурация

Настройки читаются из `config.toml` (пример — `config.toml.example`) и переопределяются
переменными окружения с разделителем `__`, например `DATABASE__POSTGRES_HOST=localhost`.

| Секция | Что настраивает |
|---|---|
| `database` | подключение к PostgreSQL; `alembic_postgres_host` — отдельный хост для миграций, если нужен |
| `s3` | адрес хранилища (внутренний и публичный для ссылок), ключи, бакет, лимит размера файла, срок жизни ссылок |
| `auth` | секрет JWT, сроки жизни токенов и сессии админки, `cookie_secure`, длина пароля |
| `cors` | разрешённые источники (по умолчанию `http://localhost:5173`) |
| `schedule` | окна пар и границы семестров |
| `notifications` | окно напоминаний, период планировщика, ping WebSocket |
| `pagination`, `dashboard`, `administration`, `logging` | размеры страниц, главной, пакетных операций, уровень логов |

Если обязательная настройка не заполнена, приложение не стартует и пишет в лог полный список
`missing_settings`.

`s3.public_endpoint_url` — адрес, который попадёт в ссылки для браузера. Внутри Docker backend
ходит в `http://minio:9000`, а браузер — в `http://localhost:9000`.

## API

- Ошибки всегда в одном формате, с подходящим HTTP-статусом:
  `{"error": {"code", "message", "details", "request_id"}}`.
- Аутентификация — JWT в httpOnly-cookie: короткий access-токен и refresh-токен, который
  уходит только на `/api/auth`. Сессии хранятся в БД; при отзыве сессии её WebSocket-соединения
  закрываются. У админки своя сессия.
- Списки постраничные (`pagination.default_per_page` / `max_per_page`).
- Файлы не идут через backend: он выдаёт presigned-ссылки на загрузку и скачивание, браузер
  работает с S3 напрямую.

Полная схема — `/docs` и `/openapi.json`. Копия схемы для фронта лежит в
`../frontend/src/shared/api/openapi.json`; после изменения API её нужно обновить и перегенерировать
типы (см. [README фронта](../frontend/README.md#типы-api)).

## Уведомления и фоновые задачи

- Триггеры БД после коммита отправляют `NOTIFY`, слушатель PostgreSQL (`core/realtime`) рассылает
  события в открытые WebSocket-соединения пользователя.
- APScheduler раз в `notifications.reminder_interval_minutes` минут создаёт напоминания о
  дедлайнах, до которых осталось меньше `reminder_window_hours` часов.

## Логи

Структурные JSON-логи в stdout (`make logs` в Docker). Каждый ответ несёт заголовок `X-Request-Id`,
тот же идентификатор есть в каждой строке лога этого запроса и в поле `request_id` ошибки.

## Миграции

```bash
make migrate MSG="add course color"   # автогенерация по моделям из src/core/db/models
make upgrade
```

Автомиграцию нужно прочитать перед коммитом: Alembic не видит триггеры, переименования и
изменения данных. Миграции, которые уже могли быть применены, не правятся — вместо этого пишется новая.

## Тесты

```bash
make test               # unit: быстрые, без Docker
make test-integration   # integration: PostgreSQL и MinIO поднимаются в Testcontainers
make test-all
```

- Слои: `tests/unit/<домен>/` и `tests/integration/<домен>/`; общие помощники — `tests/support/`.
- Каждый тест помечен `@pytest.mark.case(id="...")` и закрывает ровно один сценарий из
  `tests/scenarios.toml`. Новый тест — новая запись в манифесте.
- Сценарий со `status = "known_bug"` превращается в `xfail(strict=True)` и должен иметь `reason`.
- Тесты не трогают ваш `config.toml`: `conftest.py` подменяет подключение переменными окружения
  до импорта настроек.

`make check` — только статика. Перед коммитом запускайте `make check` и `make test-all`.
