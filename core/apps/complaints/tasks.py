from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from celery import shared_task
from django.conf import settings

from core.apps.complaints.models import Category, IncomingReport, IncomingStatus
from core.apps.complaints.services import attach_to_master


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


@shared_task(name="complaints.run_ai_check")
def run_ai_check(incoming_id: int) -> None:
    try:
        incoming = IncomingReport.objects.select_related("user").get(pk=incoming_id)
        ml_response = _call_ml_service(
            {
                "category": incoming.declared_category,
                "photo_url": _photo_url(incoming),
                "text": incoming.text,
            }
        )

        confidence = float(ml_response["confidence"])
        is_match = bool(ml_response["is_match"])
        pred_category = _normalize_pred_category(ml_response.get("pred_category"))
    except (
        IncomingReport.DoesNotExist,
        KeyError,
        TypeError,
        ValueError,
        error.HTTPError,
        error.URLError,
        json.JSONDecodeError,
    ):
        if "incoming" not in locals():
            return
        incoming.status = IncomingStatus.NEEDS_MODERATION
        incoming.save(update_fields=["status", "updated_at"])
        return

    incoming.ai_pred_category = pred_category
    incoming.ai_confidence = confidence

    if is_match and confidence >= settings.AI_MATCH_THRESHOLD:
        incoming.status = IncomingStatus.PROCESSED
        attach_to_master(incoming)
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
