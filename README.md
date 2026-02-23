# Metricity

Backend: Django + DRF + PostgreSQL + Redis + Celery.

## Требования
- Docker / Docker Compose v2
- uv (https://github.com/astral-sh/uv) или Python 3.13+ локально

## Быстрый старт
```bash
# 1. Скопировать переменные окружения
cp .env.example .env

# 2. Поднять базы и Redis
docker compose -f docker_compose/storages.yaml --env-file .env up -d

# 3. Собрать и запустить backend + воркеры
docker compose -f docker_compose/app.yaml -f docker_compose/storages.yaml --env-file .env up --build -d

# 4. Применить миграции
docker compose -f docker_compose/app.yaml -f docker_compose/storages.yaml exec main-app python manage.py migrate

# 5. (опционально) создать суперпользователя
docker compose -f docker_compose/app.yaml -f docker_compose/storages.yaml exec main-app python manage.py createsuperuser

# 6. Проверить проект
docker compose -f docker_compose/app.yaml -f docker_compose/storages.yaml exec main-app python manage.py check
```

## Полезно знать
- Приложение доступно на порту, указанном в `DJANGO_PORT` (по умолчанию 8000).
- Swagger / OpenAPI: `/api/schema/` (drf-spectacular), UI `/api/schema/swagger-ui/` после добавления URL.
- Celery использует Redis: `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`.

## Сервисы compose
- `main-app` — Django runserver (dev).
- `postgres` — база данных, volume `postgres_data` в `/var/lib/postgresql/data`.
- `redis` — брокер/кеш, volume `redis_data`.
- `celery-worker`, `celery-beat` — асинхронные задачи.
