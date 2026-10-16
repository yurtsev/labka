.PHONY: help \
        up down build logs ps \
        upgrade downgrade migrate \
        format lint lint-fix typecheck check \
        test test-integration test-all \
        run create-admin create-admin-docker seed seed-reset

SRC := src tests
TESTS := tests

help:
	@echo ""
	@echo "  Docker"
	@echo "    up                        собрать и поднять backend (сначала make -C ../infra up)"
	@echo "    down                      остановить и убрать backend"
	@echo "    build                     пересобрать образ backend"
	@echo "    logs                      логи всех контейнеров"
	@echo "    ps                        статус контейнеров"
	@echo ""
	@echo "  Миграции"
	@echo "    upgrade                   применить все миграции"
	@echo "    downgrade REV=<rev>       откатить до ревизии"
	@echo "    migrate MSG=<msg>         создать автомиграцию"
	@echo ""
	@echo "  Качество кода"
	@echo "    check                     формат + линт + типы"
	@echo "    format                    форматирование ruff"
	@echo "    lint                      проверка линтером"
	@echo "    lint-fix                  форматирование + автоисправление линтера"
	@echo "    typecheck                 проверка типов mypy"
	@echo ""
	@echo "  Тесты"
	@echo "    test                      unit-тесты (без Docker)"
	@echo "    test-integration          integration-тесты (PostgreSQL в Testcontainers, нужен Docker)"
	@echo "    test-all                  все тесты"
	@echo ""
	@echo "  Разработка"
	@echo "    run                       запустить приложение локально (без docker)"
	@echo "    create-admin              создать админа (спросит почту, ФИО и пароль)"
	@echo "    create-admin-docker       то же в запущенном make up контейнере backend"
	@echo "    seed                      наполнить пустую базу тестовыми данными (пароль labka2026)"
	@echo "    seed-reset                очистить базу и наполнить тестовыми данными заново"
	@echo ""

# === Docker ===

up:
	@docker network inspect labka >/dev/null 2>&1 || { echo "Нет сети labka: сначала подними окружение — make -C ../infra up"; exit 1; }
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build backend

logs:
	docker compose logs -f

ps:
	docker compose ps

# === Migrations ===

upgrade:
	uv run alembic upgrade head

downgrade:
	uv run alembic downgrade $(REV)

migrate:
	uv run alembic revision --autogenerate -m "$(MSG)"

# === Dev ===

run:
	uv run python -m src

create-admin:
	uv run python -m src.admin.cli

create-admin-docker:
	docker compose exec backend python -m src.admin.cli

# Скрипт запускается с хоста, поэтому Postgres берётся с проброшенного порта, а не по имени сервиса.
seed:
	DATABASE__POSTGRES_HOST=localhost uv run python -m scripts.seed

seed-reset:
	DATABASE__POSTGRES_HOST=localhost uv run python -m scripts.seed --reset

# === Tests ===

test:
	uv run pytest $(TESTS) --suite=unit

test-integration:
	uv run pytest $(TESTS) --suite=integration

test-all:
	uv run pytest $(TESTS) --suite=full

# === Quality ===

format:
	uv run ruff format $(SRC)

lint:
	uv run ruff check $(SRC)

lint-fix:
	uv run ruff format $(SRC)
	uv run ruff check --fix $(SRC)

typecheck:
	uv run mypy $(SRC)

check:
	uv run ruff format --check $(SRC)
	uv run ruff check $(SRC)
	uv run mypy $(SRC)
