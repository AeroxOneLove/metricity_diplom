DC = docker compose
APP_FILE = docker_compose/app.yaml
STORAGES_FILE = docker_compose/storages.yaml
ENV = --env-file .env
APP_STACK = -f $(APP_FILE) -f $(STORAGES_FILE) $(ENV)
STORAGES_STACK = -f $(STORAGES_FILE) $(ENV)

.PHONY: storages up makemigrations migrate superuser check down down-v logs logs_app collectstatic

storages:
	$(DC) $(STORAGES_STACK) up -d

up:
	$(DC) $(APP_STACK) up --build -d

migrate:
	$(DC) $(APP_STACK) exec main-app python manage.py migrate

showmigrations:
	$(DC) $(APP_STACK) exec main-app python manage.py showmigrations

makemigrations:
	$(DC) $(APP_STACK) exec main-app python manage.py makemigrations

superuser:
	$(DC) $(APP_STACK) exec main-app python manage.py createsuperuser

check:
	$(DC) $(APP_STACK) exec main-app python manage.py check

down:
	$(DC) $(APP_STACK) down

down-v:
	$(DC) $(APP_STACK) down -v

logs:
	$(DC) $(APP_STACK) logs -f

logs_app:
	$(DC) $(APP_STACK) logs -f main-app

shell:
	docker compose -f docker_compose/app.yaml -f docker_compose/storages.yaml --env-file .env exec main-app python manage.py shell

collectstatic: ## Собрать статические файлы Django
	$(DC) $(APP_STACK) exec main-app python manage.py collectstatic --noinput
