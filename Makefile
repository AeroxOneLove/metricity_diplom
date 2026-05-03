DC = docker compose
APP_FILE = docker_compose/app.yaml
STORAGES_FILE = docker_compose/storages.yaml
ENV = --env-file .env
APP_STACK = -f $(APP_FILE) -f $(STORAGES_FILE) $(ENV)
STORAGES_STACK = -f $(STORAGES_FILE) $(ENV)

.PHONY: init up makemigrations migrate showmigrations superuser check test tests seed_demo down down-v logs logs_app logs_beat shell collectstatic

init: up makemigrations migrate

up:
	$(DC) $(APP_STACK) up --build -d

migrate:
	$(DC) $(APP_STACK) exec main-app python manage.py migrate

makemigrations:
	$(DC) $(APP_STACK) exec main-app python manage.py makemigrations

superuser:
	$(DC) $(APP_STACK) exec main-app python manage.py createsuperuser

check:
	$(DC) $(APP_STACK) exec main-app python manage.py check

test:
	$(DC) $(APP_STACK) exec main-app python manage.py test

tests: test

seed_demo:
	$(DC) $(APP_STACK) exec main-app python manage.py seed_demo

showmigrations:
	$(DC) $(APP_STACK) exec main-app python manage.py showmigrations

down:
	$(DC) $(APP_STACK) down

down-v:
	$(DC) $(APP_STACK) down -v

logs:
	$(DC) $(APP_STACK) logs -f

logs_app:
	$(DC) $(APP_STACK) logs -f main-app

logs_beat:
	$(DC) $(APP_STACK) logs -f celery-beat

shell:
	$(DC) $(APP_STACK) exec main-app python manage.py shell
