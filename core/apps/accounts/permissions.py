from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission

from .models import UserLevel
from .services import level_rank


def get_user_level(user) -> str | None:
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.profile.level
    except ObjectDoesNotExist:
        return None


def has_min_level(user, minimum_level: str) -> bool:
    user_level = get_user_level(user)
    if user_level is None:
        return False
    return level_rank(user_level) >= level_rank(minimum_level)


class IsTrusted(BasePermission):
    message = "Требуется уровень TRUSTED или выше."

    def has_permission(self, request, view) -> bool:
        return has_min_level(request.user, UserLevel.TRUSTED)


class CanSetPriority(BasePermission):
    message = "Требуется уровень ACTIVE или выше."

    def has_permission(self, request, view) -> bool:
        return has_min_level(request.user, UserLevel.ACTIVE)


class IsModerator(BasePermission):
    message = "Требуется уровень MODERATOR."

    def has_permission(self, request, view) -> bool:
        return get_user_level(request.user) == UserLevel.MODERATOR
