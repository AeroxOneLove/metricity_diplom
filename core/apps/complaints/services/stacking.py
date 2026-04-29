from __future__ import annotations

from decimal import Decimal

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models.fields.files import FieldFile

from core.apps.complaints.models import Complaint, ComplaintStatus, IncomingReport, StackReport

from .geo import DUPLICATE_RADIUS_M, haversine_m, make_cell_id, neighbor_cells


ACTIVE_COMPLAINT_STATUSES: tuple[str, str] = (
    ComplaintStatus.PUBLISHED,
    ComplaintStatus.IN_PROGRESS,
)


def _to_float(value: Decimal | float | int | str) -> float:
    return float(value)


def _create_new_master(incoming: IncomingReport, cell_id: str) -> Complaint:
    return Complaint.objects.create(
        category=incoming.declared_category,
        lat=incoming.lat,
        lon=incoming.lon,
        cell_id=cell_id,
        stack_count=0,
        priority_score=0,
        ai_verified=bool(
            incoming.ai_pred_category
            and incoming.ai_pred_category == incoming.declared_category
            and incoming.ai_confidence is not None
        ),
        ai_confidence=float(incoming.ai_confidence or 0),
    )


def _attach_stack_report(
    *,
    complaint: Complaint,
    user_id: int,
    text: str = "",
    photo: UploadedFile | FieldFile | None = None,
) -> bool:
    _, created = StackReport.objects.get_or_create(
        complaint=complaint,
        user_id=user_id,
        defaults={
            "text": text,
            "photo": photo,
        },
    )

    if created:
        complaint.stack_count += 1
        complaint.priority_score = _to_float(complaint.stack_count)
        complaint.save(update_fields=["stack_count", "priority_score", "updated_at"])

    return created


def attach_to_master(incoming: IncomingReport) -> Complaint:
    """
    Привязывает входящий репорт к мастер-жалобе или создаёт новую.

    Повторное прикрепление того же пользователя не увеличивает стек,
    потому что `StackReport` уникален по паре `(complaint, user)`.
    """

    incoming_cell_id = make_cell_id(incoming.lat, incoming.lon)
    incoming.cell_id = incoming_cell_id

    with transaction.atomic():
        candidate_ids = neighbor_cells(incoming_cell_id)
        candidates = list(
            Complaint.objects.filter(
                category=incoming.declared_category,
                status__in=ACTIVE_COMPLAINT_STATUSES,
                cell_id__in=candidate_ids,
            )
        )

        nearest: Complaint | None = None
        nearest_distance: float | None = None

        for candidate in candidates:
            distance = haversine_m(incoming.lat, incoming.lon, candidate.lat, candidate.lon)
            if nearest_distance is None or distance < nearest_distance:
                nearest = candidate
                nearest_distance = distance

        if nearest is None or nearest_distance is None or nearest_distance > DUPLICATE_RADIUS_M:
            master = _create_new_master(incoming=incoming, cell_id=incoming_cell_id)
        else:
            master = Complaint.objects.select_for_update().get(pk=nearest.pk)

        _attach_stack_report(
            complaint=master,
            user_id=incoming.user_id,
            text=incoming.text,
            photo=incoming.photo,
        )

        return master


def confirm_complaint(
    *,
    complaint: Complaint,
    user_id: int,
    text: str = "",
    photo: UploadedFile | FieldFile | None = None,
) -> tuple[Complaint, bool]:
    if complaint.status not in ACTIVE_COMPLAINT_STATUSES:
        raise ValueError("Подтверждать можно только активные жалобы.")

    with transaction.atomic():
        locked_complaint = Complaint.objects.select_for_update().get(pk=complaint.pk)
        created = _attach_stack_report(
            complaint=locked_complaint,
            user_id=user_id,
            text=text,
            photo=photo,
        )
        return locked_complaint, created
