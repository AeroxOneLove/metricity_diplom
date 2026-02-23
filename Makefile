DC = docker compose
APP_FILE = docker_compose/app.yaml
STORAGES_FILE = docker_compose/storages.yaml
ENV = --env-file .env
APP_STACK = -f $(APP_FILE) -f $(STORAGES_FILE) $(ENV)
STORAGES_STACK = -f $(STORAGES_FILE) $(ENV)

.PHONY: storages up migrate superuser check down down-v logs

storages:
	$(DC) $(STORAGES_STACK) up -d

up:
	$(DC) $(APP_STACK) up --build -d

migrate:
	$(DC) $(APP_STACK) exec main-app python manage.py migrate

superuser:
	$(DC) $(APP_STACK) exec main-app python manage.py createsuperuser

down:
	$(DC) $(APP_STACK) down

down-v:
	$(DC) $(APP_STACK) down -v

logs:
	$(DC) $(APP_STACK) logs -f
