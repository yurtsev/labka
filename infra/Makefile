.PHONY: help up down logs ps

help:
	@echo ""
	@echo "  Окружение (Postgres, MinIO, мониторинг, сеть labka)"
	@echo "    up                        поднять окружение"
	@echo "    down                      остановить и убрать окружение (тома остаются)"
	@echo "    logs                      логи всех контейнеров"
	@echo "    ps                        статус контейнеров"
	@echo ""

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps
