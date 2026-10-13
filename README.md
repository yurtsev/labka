# Labka

Трекер лабораторных работ и домашних заданий для вуза. Преподаватель ведёт курсы, публикует
задания, материалы и объявления, составляет расписание и проверяет работы. Студент видит курсы
своей группы, сдаёт работы, следит за дедлайнами, оценками и занятиями в одном календаре и ведёт
личные задачи. Администратор заводит структуру вуза, группы, студентов и преподавателей.

> **Статус.** Backend (REST API, WebSocket, админка) готов и покрыт тестами. Каталог `frontend/`
> пока пуст: веб-приложение на React ещё не начато, поэтому снимков экранов в
> `docs/screenshots/` нет.

## Что умеет

- **Роли:** студент, преподаватель, администратор (админка на `/admin`). Регистрируется только студент —
  по коду группы и почте из списка группы; преподавателя создаёт администратор.
- **Курсы:** привязаны к семестру (осенний или весенний), группам, шкале оценок (диапазон или зачёт);
  архив — только чтение.
- **Материалы, объявления, задания** (лабораторные, практики, домашние), дедлайны мягкие и жёсткие,
  файлы в S3-хранилище.
- **Сдача и проверка:** попытки с файлами и комментарием, вердикт «принято» или «на доработку»,
  оценка, очередь на проверку у преподавателя.
- **Расписание и календарь:** пары только в окнах звонков, повтор каждую неделю / по чётным / по нечётным,
  разовые занятия, зачёты и экзамены; календарь на день, неделю и месяц с номером и чётностью недели.
- **Итоговые результаты:** зачёт — «зачтено / не зачтено», дифф. зачёт и экзамен — оценка 2–5.
- **Уведомления** в реальном времени по WebSocket и напоминания о дедлайнах за сутки.
- **Главная:** ближайший дедлайн, занятия и курсы; у преподавателя — число работ на проверке.

Подробно: [требования](docs/spec.md), [сценарии](docs/use-cases.md), [экраны](docs/screens.md),
[план разработки](docs/plan.md).

## Состав репозитория

```
backend/    FastAPI-сервис, миграции, тесты, docker-compose backend
docs/       требования, сценарии, экраны, план
frontend/   веб-приложение (пока пусто)
infra/      docker-compose окружения: Postgres, MinIO, мониторинг, общая сеть labka
```

## Технологии

Python 3.14 · FastAPI · uvicorn · dishka (внедрение зависимостей) · SQLAlchemy 2 (async) + asyncpg ·
Alembic · PostgreSQL 18 · S3 (MinIO локально) · APScheduler · sqladmin · pydantic-settings ·
Prometheus + Grafana + Loki + Alloy (мониторинг и логи) · pytest, Testcontainers,
ruff, mypy · менеджер пакетов `uv`.

Зависимости фиксируются в `backend/pyproject.toml` и `backend/uv.lock`.

## Модель данных

| Область | Таблицы |
|---|---|
| Структура вуза | `faculties`, `departments`, `directions`, `groups` |
| Пользователи и вход | `users`, `sessions`, `group_invites` (почты группы для регистрации), `teacher_groups` |
| Курсы | `courses`, `course_groups`, `course_materials` + `course_material_files`, `announcements` |
| Задания и проверка | `assignments` + `assignment_files`, `submissions` + `submission_files`, `reviews` |
| Расписание | `schedule_rules`, `extra_lessons`, `course_exams`, `final_grades` |
| Личное и уведомления | `personal_tasks`, `notifications` |

Статус работы студента по заданию и текущая оценка не хранятся: считаются по попыткам и проверкам.
Расписание не хранится сеткой: занятия вычисляются из правил и семестра курса. Схема описана
миграциями Alembic (`backend/alembic/versions`).

## Настройка и запуск

Нужны Docker, [uv](https://docs.astral.sh/uv/) и Python 3.14.

### Backend и окружение (всё в Docker)

Окружение (`infra/`) поднимается отдельно и создаёт Docker-сеть `labka`; backend (а позже frontend)
поднимается своим compose-файлом и подключается к этой сети.

```bash
cd infra
cp .env.example .env                    # пароли Postgres, MinIO, Grafana — заменить на свои
make up                                 # Postgres, MinIO, мониторинг, сеть labka

cd ../backend
cp config.toml.example config.toml      # настройки приложения; учётки БД и S3 — как в infra/.env
make up                                 # миграции и backend
make create-admin-docker                # создать администратора: спросит почту, ФИО и пароль
```

После запуска:

| Что | Адрес |
|---|---|
| API и документация | http://localhost:8000/docs |
| Админка | http://localhost:8000/admin |
| WebSocket уведомлений | ws://localhost:8000/api/ws |
| Консоль MinIO | http://localhost:9001 |
| Grafana | http://localhost:3000 |

Остановить: `make down` в `backend/` и `infra/`. Логи: `make logs` там же.

### Мониторинг

Alloy собирает метрики сервера, контейнеров, Postgres и backend в Prometheus (30 дней, до 5 ГБ)
и логи всех контейнеров в Loki (14 дней). В Grafana, папка Labka:

- **Сервер** — CPU, load average, память и swap, диски, сеть;
- **Контейнеры** — CPU, память, сеть и диск по каждому контейнеру, время с последнего перезапуска;
- **Backend** — запросы, ошибки, задержки, самые медленные ручки, ресурсы процесса;
- **Postgres** — соединения, транзакции, кэш, блокировки, размер БД;
- **Логи** — ошибки с traceback, упавшие и медленные запросы, поиск по всем логам. Каждый ответ API
  несёт `X-Request-Id`; если вставить его в фильтр `request_id`, останутся логи только этого запроса.

### Backend без Docker

Нужен запущенный PostgreSQL и S3-совместимое хранилище — например, окружение из `infra/`
(`make -C infra up`). В `config.toml` для этого поменять `postgres_host` на `localhost` и `s3.endpoint_url`
на `http://localhost:9000`: по умолчанию там адреса внутри Docker-сети.

```bash
cd backend
uv sync
make upgrade        # применить миграции
make run            # запустить на http://localhost:8000
make create-admin   # создать администратора
```

Приложение запускается с одним воркером: планировщик и реестр WebSocket-соединений живут в
процессе.

### Frontend

Веб-приложение ещё не реализовано, поэтому способа запуска пока нет. Когда оно появится, его
запуск и адрес API (`http://localhost:8000`, cookie-сессия, CORS через `cors.origins`)
будут описаны здесь.

### Тесты и проверки

```bash
cd backend
make check          # форматирование, линтер, типы
make test           # unit-тесты, без Docker
make test-all       # unit + integration (нужен Docker: PostgreSQL и MinIO в Testcontainers)
```

Каждый тест помечен сценарием из `backend/tests/scenarios.toml`.

## Конфигурация и секреты

Настройки читаются из `backend/config.toml` и переопределяются переменными окружения с разделителем
`__` (например, `DATABASE__POSTGRES_HOST`). Backend в Docker берёт всё из `config.toml`, поэтому
для него там указываются адреса внутри сети: `postgres` и `http://minio:9000`. Секреты окружения (Postgres, MinIO, Grafana) — в `infra/.env`;
учётки БД и S3 в `backend/config.toml` должны с ними совпадать.
Файлы `.env` и `config.toml` в репозиторий не попадают; примеры без секретов —
`infra/.env.example` и `backend/config.toml.example`. Перед первым запуском замените все
значения `change-me`.

## API

Корень — `/api`; ошибки приходят в формате `{"error": {"code", "message", "details", "request_id"}}`
с подходящим HTTP-статусом. Основные разделы (полный перечень — в `/docs`):

`auth` · `profile` · `home` · `courses` · `materials` · `announcements` · `assignments` · `submissions` ·
`reviews` · `feed` · `schedule` · `calendar` · `personal-tasks` · `exams` · `final-grades` ·
`notifications` · `ws` (WebSocket).
