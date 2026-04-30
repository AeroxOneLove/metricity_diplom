from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum

from core.apps.accounts.models import UserLevel
from core.apps.accounts.services import level_rank
from core.apps.complaints.models import Complaint, ComplaintImportanceVote, StackReport


TRUSTED_STACK_REPORT_BONUS = 2


def _trusted_bonus(complaint: Complaint) -> int:
    bonus = 0
    stack_reports = StackReport.objects.filter(complaint=complaint).select_related("user__profile")

    for stack_report in stack_reports:
        try:
            user_level = stack_report.user.profile.level
        except (AttributeError, ObjectDoesNotExist):
            continue
        if level_rank(user_level) >= level_rank(UserLevel.TRUSTED):
            bonus += TRUSTED_STACK_REPORT_BONUS

    return bonus


def _importance_score(complaint: Complaint) -> int:
    aggregate = ComplaintImportanceVote.objects.filter(complaint=complaint).aggregate(
        total=Sum("weight")
    )
    return int(aggregate["total"] or 0)


def recalculate_priority_score(complaint: Complaint) -> Complaint:
    stack_count = StackReport.objects.filter(complaint=complaint).count()
    complaint.stack_count = stack_count
    complaint.priority_score = stack_count + _trusted_bonus(complaint) + _importance_score(complaint)
    complaint.save(update_fields=["stack_count", "priority_score", "updated_at"])
    return complaint
