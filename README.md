# Metricity

Django + DRF + PostgreSQL + Redis + Celery.

## Dev-запуск

Проект читает переменные из `.env`. Для локальной разработки достаточно текущего compose-стека:

```bash
make up
make migrate
```

После запуска:

- API/docs: `http://localhost:8000/`
- Админка: `http://localhost:8000/admin/`
- Логи приложения: `make logs_app`

Если нужен только PostgreSQL и Redis:

```bash
make storages
```

## Основные переменные `.env`

- `DEBUG=True`
- `DJANGO_PORT=8000`
- `POSTGRES_HOST=postgres`
- `POSTGRES_PORT=5432` - внешний порт PostgreSQL на хосте
- `POSTGRES_DB_PORT=5432` - порт PostgreSQL внутри docker-сети для Django
- `REDIS_PORT=6379`
- `CELERY_BROKER_URL=redis://redis:6379/0`
- `CELERY_RESULT_BACKEND=redis://redis:6379/1`
- `ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0`
- `CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000`

## Команды

- `make up` - собрать и запустить приложение, celery-worker, PostgreSQL и Redis
- `make migrate` - применить миграции
- `make makemigrations` - создать миграции
- `make superuser` - создать суперпользователя
- `make check` - проверить Django-конфигурацию
- `make logs` / `make logs_app` - смотреть логи
- `make down` / `make down-v` - остановить стек, с удалением volume во втором случае

## Текущий dev-стек

- `main-app` - Django `runserver`, порт берется из `DJANGO_PORT`
- `postgres` - база данных
- `redis` - брокер Celery
- `celery-worker` - обработчик фоновых задач
