# Labka — backend

FastAPI-сервис Labka. Общее описание проекта, требования и запуск целиком — в
[корневом README](../README.md); здесь — то, что нужно при работе с кодом backend.

## Команды

```
make help
```

- `up` / `down` / `build` / `logs` / `ps` — docker-compose backend (миграции и сервис); окружение — в `../infra`
- `upgrade` / `downgrade REV=<rev>` / `migrate MSG=<msg>` — миграции Alembic
- `check` / `lint-fix` / `format` / `lint` / `typecheck` — качество кода
- `test` / `test-integration` / `test-all` — тесты (интеграционным нужен Docker)
- `run` — запуск без Docker, `create-admin` / `create-admin-docker` — создание администратора

## Структура `src/`

```
main.py         сборка приложения: контейнер зависимостей, middleware, роутеры, запуск слушателя и планировщика
config/         настройки (pydantic-settings), доступ через `from src.config import cfg`
admin/          sqladmin на /admin: структура вуза, группы, почты, преподаватели, студенты
api/<домен>/    router / schemas / service (+ presenter, parser, dto, utils)
api/exc/        ошибки доменов и единый обработчик ошибок
core/db/        модели, репозитории, unit of work
core/<система>/ общая подсистема: access, grading, schedule, notifications, realtime, scheduler, s3, security
core/di/        провайдеры dishka
```

Слои: router → service → unit of work / репозитории → модели. Зависимости идут только вниз: API-домены
не импортируют друг друга, `core` не импортирует `api` (кроме провайдеров в `core/di`).

## Конфигурация

`config.toml` (пример — `config.toml.example`) и переменные окружения с разделителем `__`.
Секции: `database`, `s3`, `pagination`, `logging`, `cors`, `auth`, `schedule` (окна пар и границы
семестров), `notifications`, `dashboard`, `administration`.

## Уведомления и фоновые задачи

Триггеры БД отправляют `NOTIFY` после коммита, слушатель PostgreSQL передаёт события в открытые
WebSocket-соединения; APScheduler раз в 5 минут создаёт напоминания о дедлайнах. Оба живут в
процессе приложения, поэтому uvicorn запускается с одним воркером.
