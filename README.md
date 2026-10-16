# Labka

Трекер лабораторных работ и домашних заданий для вуза.

- **Преподаватель** ведёт курсы, публикует задания, материалы и объявления, составляет расписание
  и проверяет работы.
- **Студент** видит курсы своей группы, сдаёт работы, следит за дедлайнами, оценками и занятиями
  в одном календаре и ведёт личные задачи.
- **Администратор** заводит структуру вуза, группы, студентов и преподавателей в админке backend.

> **Статус.** Backend (REST API, WebSocket, админка) готов и покрыт тестами. Веб-приложение
> реализует все экраны студента и преподавателя.

## Что умеет

- **Роли и вход.** Регистрируется только студент — по коду группы и почте из списка группы.
  Преподавателя и администратора создаёт администратор.
- **Курсы** привязаны к семестру (осенний или весенний), группам и шкале оценок (диапазон или
  зачёт). Завершённые курсы уходят в архив и доступны только для чтения.
- **Материалы, объявления и задания** (лабораторные, практики, домашние) с мягкими и жёсткими
  дедлайнами. Файлы хранятся в S3.
- **Сдача и проверка.** Попытки с файлами и комментарием, вердикт «принято» или «на доработку»,
  оценка, общая очередь на проверку у преподавателя.
- **Расписание и календарь.** Пары ставятся в окна звонков и повторяются каждую неделю, по чётным
  или по нечётным; есть разовые занятия, зачёты и экзамены. Календарь на день, неделю и месяц.
- **Уведомления** в реальном времени по WebSocket и напоминания о дедлайнах за сутки.

## Экраны

| Экран | Адрес | Кто |
|---|---|---|
| Вход, регистрация студента | `/login`, `/register` | гость |
| Главная: ближайший дедлайн или «ждут проверки», занятия, курсы | `/` | все |
| Курс: лента с фильтром, материалы, расписание и экзамены | `/courses/:id` | все |
| Задание: у студента — сдача и история попыток, у преподавателя — таблица студентов | `/courses/:id/assignments/:id` | все |
| Календарь, личные задачи | `/calendar` | все |
| Уведомления | `/notifications` | все |
| Профиль: аватарка, смена пароля, выход | `/profile` | все |
| Архив курсов | `/courses/archive` | все |
| Новый курс, настройки курса | `/courses/new`, `/courses/:id/settings` | преподаватель |
| Создание и правка задания | `/courses/:id/assignments/new`, `…/edit` | преподаватель |
| Очередь на проверку, проверка попытки | `/reviews`, `…/students/:id` | преподаватель |
| Админка: структура вуза, группы, преподаватели, студенты | `/admin` (backend) | администратор |

Подробно — [экраны](docs/screens.md) и [сценарии](docs/scenarios.md).

## Модель данных

| Область | Таблицы |
|---|---|
| Структура вуза | `faculties`, `departments`, `directions`, `groups` |
| Пользователи и вход | `users`, `sessions`, `group_invites` (почты группы для регистрации), `teacher_groups` |
| Курсы | `courses`, `course_groups`, `course_materials` + `course_material_files`, `announcements` |
| Задания и проверка | `assignments` + `assignment_files`, `submissions` + `submission_files`, `reviews` |
| Расписание | `schedule_rules`, `extra_lessons`, `course_exams` |
| Личное и уведомления | `personal_tasks`, `notifications` |

Статус работы студента и текущая оценка не хранятся, а считаются по попыткам и проверкам.
Занятия тоже не хранятся сеткой: они вычисляются из правил расписания и семестра курса. Схема
задаётся миграциями Alembic (`backend/alembic/versions`).
Поля, ключи и связи — в [docs/data-model.md](docs/data-model.md).

## Состав репозитория

| Папка | Что внутри |
|---|---|
| [`infra/`](infra/README.md) | Окружение в Docker: PostgreSQL, MinIO, общая сеть `labka` |
| [`backend/`](backend/README.md) | FastAPI-сервис: REST API, WebSocket, админка, миграции, тесты |
| [`frontend/`](frontend/README.md) | Веб-приложение на React + TypeScript |
| [`docs/`](docs/README.md) | Сценарии, экраны, модель данных, архитектура, API, скриншоты |

Как части связаны:

```
браузер ──► frontend (Vite, :5173) ──/api, /api/ws──► backend (:8000) ──► PostgreSQL (:5432)
                                                           │
                                                           └──────────► MinIO / S3 (:9000)
```

Файлы браузер скачивает и загружает напрямую в S3 по подписанным ссылкам, которые выдаёт backend.

## Быстрый старт

Нужны Docker, Node.js 22+, для разработки backend — [uv](https://docs.astral.sh/uv/) и Python 3.14.
Окружение и backend поднимаются в Docker, фронт — через Vite:

```bash
cd infra
cp .env.example .env                 # заменить все change-me
make up                              # PostgreSQL, MinIO, сеть labka

cd ../backend
cp config.toml.example config.toml   # учётки БД и S3 — те же, что в infra/.env
make up                              # миграции и backend
make create-admin-docker             # первый администратор: спросит почту, ФИО и пароль

cd ../frontend
cp .env.example .env
npm install
npm run dev                          # http://localhost:5173
```

| Что | Адрес |
|---|---|
| Веб-приложение | http://localhost:5173 |
| API и Swagger | http://localhost:8000/docs |
| Админка | http://localhost:8000/admin |
| WebSocket уведомлений | ws://localhost:8000/api/ws |
| Консоль MinIO | http://localhost:9001 |

Дальше администратор в админке заводит структуру вуза, группы со списками почт и
преподавателей; преподаватель создаёт курсы в приложении; студент регистрируется сам по коду группы.

Остановить: `make down` в `backend/` и `infra/` (данные остаются в томах Docker).

## Конфигурация и секреты

| Файл | Кто читает | Пример |
|---|---|---|
| `infra/.env` | docker-compose окружения: пароли PostgreSQL и MinIO | `infra/.env.example` |
| `backend/config.toml` | backend: БД, S3, JWT, расписание, лимиты | `backend/config.toml.example` |
| `frontend/.env` | Vite: лимиты форм | `frontend/.env.example` |

Настоящие файлы в git не попадают. Значения, которые должны совпадать:

- учётки БД и S3 в `backend/config.toml` ↔ `infra/.env`;
- размер файла и длина пароля в `frontend/.env` ↔ `[s3]` и `[auth]` в `backend/config.toml`.

Без обязательных настроек ни backend, ни frontend не стартуют и называют каждую незаполненную.

## Технологии

**Backend:** Python 3.14, FastAPI, dishka, SQLAlchemy 2 (async) + asyncpg, Alembic, PostgreSQL 18,
S3 (MinIO), APScheduler, sqladmin, pytest + Testcontainers, ruff, mypy, uv.

**Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query, shadcn/ui (Radix) +
Tailwind CSS 4, React Hook Form + Zod, Motion, openapi-fetch, oxlint.
