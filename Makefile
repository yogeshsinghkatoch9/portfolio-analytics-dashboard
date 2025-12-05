.PHONY: build up down logs ps restart

build:
	@docker-compose build

up:
	@docker-compose up -d --build

down:
	@docker-compose down

logs:
	@docker-compose logs -f

ps:
	@docker-compose ps

restart:
	@docker-compose down && docker-compose up -d --build

.PHONY: frontend

frontend:
	@echo "Starting frontend dev server (npm start)"
	@npm start
