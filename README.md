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
backend/    FastAPI-сервис, миграции, тесты, docker-compose со всем окружением
docs/       требования, сценарии, экраны, план
frontend/   веб-приложение (пока пусто)
infra/      зарезервировано под инфраструктуру (пока пусто)
```

## Технологии

Python 3.14 · FastAPI · uvicorn · dishka (внедрение зависимостей) · SQLAlchemy 2 (async) + asyncpg ·
Alembic · PostgreSQL 18 · S3 (MinIO локально) · APScheduler · sqladmin · pydantic-settings ·
Prometheus + Grafana + Loki + Promtail + cAdvisor (мониторинг и логи) · pytest, Testcontainers,
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

### Backend и база данных (всё в Docker)

```bash
cd backend
cp .env.example .env                    # пароли Postgres, MinIO, Grafana — заменить на свои
cp config.toml.example config.toml      # настройки приложения
make up                                 # Postgres, MinIO, миграции, backend, мониторинг
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

Остановить: `make down`. Логи: `make logs`.

### Backend без Docker

Нужен запущенный PostgreSQL и S3-совместимое хранилище (можно поднять только их:
`docker compose up -d postgres minio minio-init`).

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
`__` (например, `DATABASE__POSTGRES_HOST`). Секреты docker-compose — в `backend/.env`.
Файлы `.env` и `config.toml` в репозиторий не попадают; примеры без секретов —
`backend/.env.example` и `backend/config.toml.example`. Перед первым запуском замените все
значения `change-me`.

## API

Корень — `/api`; ошибки приходят в формате `{"error": {"code", "message", "details", "request_id"}}`
с подходящим HTTP-статусом. Основные разделы (полный перечень — в `/docs`):

`auth` · `profile` · `home` · `courses` · `materials` · `announcements` · `assignments` · `submissions` ·
`reviews` · `feed` · `schedule` · `calendar` · `personal-tasks` · `exams` · `final-grades` ·
`notifications` · `ws` (WebSocket).
