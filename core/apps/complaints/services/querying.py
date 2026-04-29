from __future__ import annotations

from collections.abc import Mapping

from django.db.models import QuerySet
from rest_framework import serializers

from core.apps.complaints.models import Category, Complaint, ComplaintStatus


BBOX_PARAMS = ("minLat", "maxLat", "minLon", "maxLon")
ALLOWED_ORDERING = {
    "priority_score",
    "-priority_score",
    "created_at",
    "-created_at",
    "stack_count",
    "-stack_count",
}


def _choice_values(choices: type[Category] | type[ComplaintStatus]) -> set[str]:
    return {value for value, _ in choices.choices}


def _parse_float(value: str, param_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError(
            {param_name: "Значение должно быть числом."}
        ) from exc


def _apply_bbox(queryset: QuerySet[Complaint], params: Mapping[str, str]) -> QuerySet[Complaint]:
    provided_params = [param_name for param_name in BBOX_PARAMS if param_name in params]
    if not provided_params:
        return queryset

    if len(provided_params) != len(BBOX_PARAMS):
        raise serializers.ValidationError(
            {
                "bbox": (
                    "Для фильтрации по bbox нужно передать все параметры: "
                    "minLat, maxLat, minLon, maxLon."
                )
            }
        )

    min_lat = _parse_float(params["minLat"], "minLat")
    max_lat = _parse_float(params["maxLat"], "maxLat")
    min_lon = _parse_float(params["minLon"], "minLon")
    max_lon = _parse_float(params["maxLon"], "maxLon")

    return queryset.filter(
        lat__gte=min_lat,
        lat__lte=max_lat,
        lon__gte=min_lon,
        lon__lte=max_lon,
    )


def filter_complaints(
    queryset: QuerySet[Complaint],
    params: Mapping[str, str],
) -> QuerySet[Complaint]:
    queryset = _apply_bbox(queryset, params)

    category = params.get("category")
    if category:
        if category not in _choice_values(Category):
            raise serializers.ValidationError(
                {"category": "Неизвестная категория жалобы."}
            )
        queryset = queryset.filter(category=category)

    complaint_status = params.get("status")
    if complaint_status:
        if complaint_status not in _choice_values(ComplaintStatus):
            raise serializers.ValidationError(
                {"status": "Неизвестный статус жалобы."}
            )
        queryset = queryset.filter(status=complaint_status)

    ordering = params.get("ordering")
    if ordering:
        if ordering not in ALLOWED_ORDERING:
            raise serializers.ValidationError(
                {"ordering": "Недопустимое поле сортировки."}
            )
        queryset = queryset.order_by(ordering)

    return queryset
