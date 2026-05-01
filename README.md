# Metricity

Backend-система для приема, AI-проверки, модерации, склейки дублей и приоритизации городских жалоб.

## Стек

- Django 6
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Docker Compose
- JWT
- Swagger/OpenAPI

## Архитектура

- `UserProfile` - профиль пользователя с рейтингом и уровнем доступа.
- `IncomingReport` - входящее обращение пользователя до AI-проверки или модерации.
- `Complaint` - опубликованная мастер-жалоба, которая показывается на карте.
- `StackReport` - подтверждение/дубль жалобы от пользователя.
- `ModerationDecision` - решение модератора по входящему обращению.
- `ComplaintImportanceVote` - ручная оценка важности жалобы пользователем с достаточным уровнем.
- `UserRatingEvent` - история изменений рейтинга пользователя.

## Основной Flow

1. Пользователь отправляет обращение: `POST /api/v1/reports/`.
2. Создается `IncomingReport` со статусом `PENDING_AI`.
3. Celery запускает задачу `run_ai_check`.
4. Если AI уверен: `IncomingReport -> PROCESSED`, затем `attach_to_master`.
5. Если AI не уверен или ML недоступен: `IncomingReport -> NEEDS_MODERATION`.
6. Модератор принимает решение через approve/reject.
7. После approve появляется или обновляется опубликованная `Complaint` на карте.
8. Confirm/stacking и importance votes пересчитывают `priority_score`.

## Запуск

Создайте `.env` в корне проекта. Минимальные переменные для локального Docker Compose:

```env
SECRET_KEY=dev-secret-key
DEBUG=True
DJANGO_PORT=8000
NGINX_PORT=8080
PUBLIC_MEDIA_URL=http://localhost:8080/media/
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB_PORT=5432
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
ML_URL=http://ml:8000
AI_MATCH_THRESHOLD=0.8
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

Запуск стека:

```bash
make up
make migrate
make superuser
```

Загруженные фото хранятся в Docker volume `media_data`. Django пишет файлы в `/app/media`, Celery читает их оттуда для ML-проверки, а `media-nginx` отдаёт эти же файлы публично по `PUBLIC_MEDIA_URL`.

Создать демо-данные:

```bash
docker compose -f docker_compose/app.yaml -f docker_compose/storages.yaml --env-file .env exec main-app python manage.py seed_demo
```

Демо-пользователи создаются с паролем `password123`:

- `newbie@example.com`
- `active@example.com`
- `trusted@example.com`
- `moderator@example.com`

Полезные команды:

```bash
make check
make logs_app
make down
```

## Swagger/OpenAPI

- Swagger UI: `/api/docs/`
- OpenAPI schema: `/api/schema/`
- Redoc: `/api/redoc/`

Корневой URL `/` перенаправляет на Swagger UI.

## API Endpoints

### Auth

- `POST /api/auth/register/`
- `POST /api/auth/token/`
- `POST /api/auth/token/refresh/`
- `POST /api/auth/token/verify/`
- `GET /api/auth/me/`

### Reports

- `POST /api/v1/reports/`

### Complaints

- `GET /api/v1/complaints/`
- `GET /api/v1/complaints/<id>/`
- `POST /api/v1/complaints/<id>/confirm/`
- `POST /api/v1/complaints/<id>/set-importance/`
- `POST /api/v1/complaints/<id>/status/`

`GET /api/v1/complaints/` поддерживает параметры:

- `minLat`, `maxLat`, `minLon`, `maxLon`
- `category`
- `status`
- `ordering`
- `page`
- `page_size`

### Moderation

- `GET /api/v1/moderation/incoming/`
- `POST /api/v1/moderation/incoming/<id>/decision/`

Approve может принять финальную категорию:

```json
{
  "decision": "APPROVE",
  "category": "ROAD"
}
```

Reject может принять причину:

```json
{
  "decision": "REJECT",
  "reason": "На фото не обнаружена проблема"
}
```

## ML Contract

Metricity отправляет в ML-сервис `multipart/form-data`:

```text
category=TRASH
text=...
photo=<binary file>
```

Ожидаемый ответ:

```json
{
  "pred_category": "TRASH",
  "confidence": 0.91,
  "is_match": true
}
```

Если ML недоступен, вернул плохой JSON или не хватает обязательных полей, `IncomingReport` переводится в `NEEDS_MODERATION`.

## Demo Scenarios

- Auto approve: создать report, ML возвращает уверенный match, `IncomingReport` становится `PROCESSED`, создается/обновляется `Complaint`.
- Moderation: report со статусом `NEEDS_MODERATION` обрабатывается через `/api/v1/moderation/incoming/<id>/decision/`.
- Duplicate stacking: близкий report той же категории приклеивается к существующей активной `Complaint`.
- Confirm: пользователь уровня `ACTIVE` или выше подтверждает жалобу через `/confirm/`.
- Importance: пользователь уровня `ACTIVE` или выше ставит важность через `/set-importance/`.
- Status change: модератор меняет статус жалобы через `/status/`.
