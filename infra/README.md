# Labka — infra

Окружение для разработки: PostgreSQL и S3-хранилище MinIO в Docker. Его поднимают первым:
compose-файл создаёт Docker-сеть `labka`, к которой потом подключается backend
(`backend/docker-compose.yml`). Общее описание проекта — в [корневом README](../README.md).

## Запуск

```bash
cp .env.example .env   # заменить все change-me
make up
```

| Команда | Что делает |
|---|---|
| `make up` | поднять окружение в фоне |
| `make down` | остановить и убрать контейнеры (данные в томах остаются) |
| `make logs` | логи всех контейнеров |
| `make ps` | статус контейнеров |

## Сервисы

| Сервис | Контейнер | Порты (только `127.0.0.1`) | Назначение |
|---|---|---|---|
| `postgres` | `labka_postgres` | 5432 | PostgreSQL 18 |
| `minio` | `labka_minio` | 9000 — S3 API, 9001 — консоль | хранилище файлов |
| `minio-init` | `labka_minio_init` | — | разовая подготовка MinIO, после неё завершается |

Внутри сети `labka` сервисы доступны по именам: `postgres:5432` и `http://minio:9000`. Именно эти
адреса стоят в `backend/config.toml.example`. С хоста — `localhost:5432` и `http://localhost:9000`.

`minio-init` (`minio/init.sh`) создаёт бакет и отдельного пользователя для backend с доступом только
к объектам этого бакета (`GetObject`, `PutObject`, `DeleteObject`). Root-учётка MinIO нужна только
для консоли. Скрипт можно запускать повторно: уже созданное он не ломает.

## Переменные `.env`

| Переменная | Что значит | Где ещё указать |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | учётка и база PostgreSQL | `[database]` в `backend/config.toml` |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | root-учётка MinIO для консоли (пароль не короче 8 символов) | — |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | учётка backend в MinIO | `[s3] access_key` / `secret_key` |
| `S3_BUCKET` | бакет для файлов (по умолчанию `labka`) | `[s3] bucket` |

Пароли PostgreSQL и учётки MinIO задаются **при первом запуске**, когда создаются тома. Если
поменять их в `.env` позже, PostgreSQL продолжит работать со старым паролем.

## Данные

Данные лежат в именованных томах `labka_postgres_data` и `labka_minio_data` и переживают
`make down`. Чтобы начать с чистого листа, остановите backend и окружение и удалите тома —
**это безвозвратно удалит все данные**:

```bash
make -C ../backend down
make down
docker volume rm labka_postgres_data labka_minio_data
```

## Полезное

```bash
docker exec -it labka_postgres psql -U <POSTGRES_USER> -d <POSTGRES_DB>   # консоль БД
```

Консоль MinIO — http://localhost:9001, вход по `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`.
