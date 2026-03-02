# Metricity

Django + DRF + PostgreSQL + Redis + Celery.

## Требования
- Docker / Docker Compose v2
- uv (https://github.com/astral-sh/uv) или Python 3.13+

## Настройка окружения
1) Скопируйте переменные: `cp .env.example .env`.
2) Обязательно задайте в `.env`:
   - `SECRET_KEY`
   - `ALLOWED_HOSTS` (через запятую)
   - `CSRF_TRUSTED_ORIGINS` в формате `http://host[:port]` или `https://...` (добавьте `http://localhost:8000` или ваш домен, иначе будет 403 CSRF в админке)
   - `POSTGRES_*`, `REDIS_PORT`, `DJANGO_PORT`, `DEBUG`
3) Поднимите базы и Redis: `make storages`
4) Запустите приложение и воркеры: `make up`
5) Примените миграции: `make migrate`
6) Создайте суперпользователя (по желанию): `make superuser`

После запуска:
- Приложение: `http://localhost:8000/` (порт берется из `DJANGO_PORT`)
- Админка: `http://localhost:8000/admin/` (403 CSRF -> проверьте, что точный origin с портом есть в `CSRF_TRUSTED_ORIGINS` и очистите cookies)

## Полезные команды (Makefile)
- `make storages` — поднять postgres и redis
- `make up` — запустить main-app, nginx, celery-worker, celery-beat
- `make migrate` / `make makemigrations`
- `make superuser`
- `make logs` / `make logs_app`
- `make check`
- `make down` / `make down-v`

## Сервисы Docker Compose
- `main-app` — Django runserver (dev)
- `nginx` — фронт для статики/медиа и прокси на app
- `postgres` — БД, volume `postgres_data`
- `redis` — брокер/кеш, volume `redis_data`
- `celery-worker`, `celery-beat` — фоновые задачи
