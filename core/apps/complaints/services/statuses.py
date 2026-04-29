from __future__ import annotations

from django.db import transaction

from core.apps.complaints.models import Complaint, ComplaintStatus


ALLOWED_STATUS_TRANSITIONS = {
    ComplaintStatus.PUBLISHED: {
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.REJECTED,
    },
    ComplaintStatus.IN_PROGRESS: {
        ComplaintStatus.RESOLVED,
        ComplaintStatus.REJECTED,
    },
}


def change_complaint_status(
    complaint: Complaint,
    new_status: str,
    moderator=None,
) -> Complaint:
    allowed_next_statuses = ALLOWED_STATUS_TRANSITIONS.get(complaint.status, set())
    if new_status not in allowed_next_statuses:
        raise ValueError(
            f"Переход из статуса {complaint.status} в {new_status} запрещён."
        )

    with transaction.atomic():
        locked_complaint = Complaint.objects.select_for_update().get(pk=complaint.pk)
        allowed_next_statuses = ALLOWED_STATUS_TRANSITIONS.get(locked_complaint.status, set())
        if new_status not in allowed_next_statuses:
            raise ValueError(
                f"Переход из статуса {locked_complaint.status} в {new_status} запрещён."
            )

        locked_complaint.status = new_status
        locked_complaint.save(update_fields=["status", "updated_at"])
        return locked_complaint
