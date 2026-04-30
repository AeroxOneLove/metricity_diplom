from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error, request

from celery import shared_task
from django.conf import settings

from core.apps.accounts.models import UserRatingReason
from core.apps.accounts.services import change_user_rating
from core.apps.complaints.models import Category, IncomingReport, IncomingStatus
from core.apps.complaints.services import attach_to_master


logger = logging.getLogger(__name__)


def _photo_url(incoming: IncomingReport) -> str:
    if not incoming.photo:
        return ""
    try:
        return incoming.photo.url
    except ValueError:
        return ""


def _predict_url() -> str:
    return f"{settings.ML_URL.rstrip('/')}/predict"


def _call_ml_service(payload: dict[str, Any]) -> dict[str, Any]:
    raw_payload = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        _predict_url(),
        data=raw_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(http_request, timeout=10) as response:
        response_body = response.read().decode("utf-8")

    parsed_response = json.loads(response_body)
    if not isinstance(parsed_response, dict):
        raise ValueError("ML-сервис вернул некорректный ответ.")
    return parsed_response


def _normalize_pred_category(raw_value: Any) -> str | None:
    allowed_values = {choice for choice, _ in Category.choices}
    if raw_value in allowed_values:
        return str(raw_value)
    return None


def _parse_confidence(raw_value: Any) -> float | None:
    if raw_value is None:
        return None
    return float(raw_value)


def _parse_is_match(raw_value: Any) -> bool:
    if not isinstance(raw_value, bool):
        raise ValueError("ML-сервис вернул некорректное поле is_match.")
    return raw_value


@shared_task(name="complaints.run_ai_check")
def run_ai_check(incoming_id: int) -> None:
    try:
        incoming = IncomingReport.objects.select_related("user").get(pk=incoming_id)
    except IncomingReport.DoesNotExist:
        logger.warning("IncomingReport %s not found for AI check.", incoming_id)
        return

    if incoming.status != IncomingStatus.PENDING_AI:
        return

    try:
        ml_response = _call_ml_service(
            {
                "category": incoming.declared_category,
                "photo_url": _photo_url(incoming),
                "text": incoming.text,
            }
        )
    except (
        TimeoutError,
        ValueError,
        error.HTTPError,
        error.URLError,
        json.JSONDecodeError,
    ) as exc:
        logger.exception("ML check failed for IncomingReport %s: %s", incoming.id, exc)
        incoming.status = IncomingStatus.NEEDS_MODERATION
        incoming.save(update_fields=["status", "updated_at"])
        return

    if not isinstance(ml_response, dict):
        logger.error("ML response is not an object for IncomingReport %s.", incoming.id)
        incoming.status = IncomingStatus.NEEDS_MODERATION
        incoming.save(update_fields=["status", "updated_at"])
        return

    pred_category = _normalize_pred_category(ml_response.get("pred_category"))
    confidence: float | None = None

    try:
        confidence = _parse_confidence(ml_response.get("confidence"))
        is_match = _parse_is_match(ml_response["is_match"])
        if confidence is None:
            raise ValueError("ML-сервис не вернул поле confidence.")
    except (KeyError, TypeError, ValueError) as exc:
        logger.exception("ML response is invalid for IncomingReport %s: %s", incoming.id, exc)
        incoming.ai_pred_category = pred_category
        incoming.ai_confidence = confidence
        incoming.status = IncomingStatus.NEEDS_MODERATION
        incoming.save(
            update_fields=[
                "status",
                "ai_pred_category",
                "ai_confidence",
                "updated_at",
            ]
        )
        return

    incoming.ai_pred_category = pred_category
    incoming.ai_confidence = confidence

    if is_match and confidence >= settings.AI_MATCH_THRESHOLD:
        incoming.status = IncomingStatus.PROCESSED
        attach_to_master(incoming)
        incoming.save(
            update_fields=[
                "cell_id",
                "status",
                "ai_pred_category",
                "ai_confidence",
                "updated_at",
            ]
        )
        change_user_rating(
            incoming.user,
            5,
            UserRatingReason.AI_APPROVED_REPORT,
            incoming_report=incoming,
        )
    else:
        incoming.status = IncomingStatus.NEEDS_MODERATION
        incoming.save(
            update_fields=[
                "cell_id",
                "status",
                "ai_pred_category",
                "ai_confidence",
                "updated_at",
            ]
        )
