from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import (
    UserLevel,
    UserProfile,
    UserRatingEvent,
    level_from_rating,
    level_rank,
    promoted_level_for_rating,
)


def _find_duplicate_rating_event(
    *,
    user,
    reason: str,
    complaint=None,
    incoming_report=None,
) -> UserRatingEvent | None:
    if incoming_report is not None:
        duplicate = UserRatingEvent.objects.filter(
            user=user,
            reason=reason,
            incoming_report=incoming_report,
        ).first()
        if duplicate is not None:
            return duplicate

    if complaint is not None:
        duplicate = UserRatingEvent.objects.filter(
            user=user,
            reason=reason,
            complaint=complaint,
        ).first()
        if duplicate is not None:
            return duplicate

    return None


def change_user_rating(
    user,
    delta: int,
    reason: str,
    complaint=None,
    incoming_report=None,
) -> UserRatingEvent:
    with transaction.atomic():
        duplicate = _find_duplicate_rating_event(
            user=user,
            reason=reason,
            complaint=complaint,
            incoming_report=incoming_report,
        )
        if duplicate is not None:
            return duplicate

        event = UserRatingEvent.objects.create(
            user=user,
            delta=delta,
            reason=reason,
            complaint=complaint,
            incoming_report=incoming_report,
        )

        profile = UserProfile.objects.select_for_update().get(user=user)
        new_rating = profile.rating + delta
        updates = {
            "rating": new_rating,
            "updated_at": timezone.now(),
        }

        if profile.level != UserLevel.MODERATOR:
            updates["level"] = level_from_rating(new_rating)

        UserProfile.objects.filter(pk=profile.pk).update(**updates)
        return event


__all__ = (
    "change_user_rating",
    "level_from_rating",
    "level_rank",
    "promoted_level_for_rating",
)
