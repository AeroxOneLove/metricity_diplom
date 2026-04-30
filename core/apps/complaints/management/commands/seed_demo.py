from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.apps.accounts.models import UserLevel, UserProfile, UserRatingEvent, UserRatingReason
from core.apps.complaints.models import (
    Category,
    Complaint,
    ComplaintImportance,
    ComplaintImportanceVote,
    ComplaintStatus,
    IMPORTANCE_WEIGHTS,
    IncomingReport,
    IncomingStatus,
    StackReport,
)
from core.apps.complaints.services.geo import make_cell_id
from core.apps.complaints.services.priority import recalculate_priority_score


User = get_user_model()
DEMO_PASSWORD = "password123"


@dataclass(frozen=True)
class DemoUser:
    email: str
    level: str
    rating: int


class Command(BaseCommand):
    help = "Seed demo users and city complaint data."

    demo_users = (
        DemoUser("newbie@example.com", UserLevel.NEWBIE, 0),
        DemoUser("active@example.com", UserLevel.ACTIVE, 10),
        DemoUser("trusted@example.com", UserLevel.TRUSTED, 50),
        DemoUser("moderator@example.com", UserLevel.MODERATOR, 100),
    )

    def handle(self, *args: Any, **options: Any) -> None:
        counters: dict[str, dict[str, int]] = defaultdict(lambda: {"created": 0, "updated": 0})

        with transaction.atomic():
            users = self._seed_users(counters)
            complaints = self._seed_complaints(counters)
            self._seed_stack_reports(users, complaints, counters)
            incoming_reports = self._seed_incoming_reports(users, counters)
            self._seed_importance_votes(users, complaints, counters)
            self._seed_rating_events(users, complaints, incoming_reports, counters)

            for complaint in complaints.values():
                recalculate_priority_score(complaint)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write("Demo users:")
        for demo_user in self.demo_users:
            self.stdout.write(f"  {demo_user.email}")
        self.stdout.write(f"Password: {DEMO_PASSWORD}")
        self.stdout.write("Objects:")
        for model_name in sorted(counters):
            created = counters[model_name]["created"]
            updated = counters[model_name]["updated"]
            self.stdout.write(f"  {model_name}: created={created}, updated={updated}")

    def _count(self, counters: dict[str, dict[str, int]], model_name: str, created: bool) -> None:
        key = "created" if created else "updated"
        counters[model_name][key] += 1

    def _seed_users(self, counters: dict[str, dict[str, int]]) -> dict[str, Any]:
        users = {}
        for demo_user in self.demo_users:
            user, created = User.objects.get_or_create(
                username=demo_user.email,
                defaults={"email": demo_user.email},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
            else:
                user.email = demo_user.email
                user.set_password(DEMO_PASSWORD)
            user.save()
            self._count(counters, "User", created)

            profile, profile_created = UserProfile.objects.get_or_create(user=user)
            profile.rating = demo_user.rating
            profile.level = demo_user.level
            profile.is_level_manual = True
            profile.save()
            self._count(counters, "UserProfile", profile_created)

            users[demo_user.level] = user
            users[demo_user.email] = user
        return users

    def _complaint_defaults(
        self,
        *,
        category: str,
        status: str,
        lat: str,
        lon: str,
        ai_verified: bool = False,
        ai_confidence: float = 0,
    ) -> dict[str, Any]:
        return {
            "category": category,
            "status": status,
            "lat": lat,
            "lon": lon,
            "cell_id": make_cell_id(lat, lon),
            "stack_count": 0,
            "priority_score": 0,
            "ai_verified": ai_verified,
            "ai_confidence": ai_confidence,
        }

    def _seed_complaints(self, counters: dict[str, dict[str, int]]) -> dict[str, Complaint]:
        specs = {
            "trash_published": self._complaint_defaults(
                category=Category.TRASH,
                status=ComplaintStatus.PUBLISHED,
                lat="56.949648",
                lon="24.105186",
                ai_verified=True,
                ai_confidence=0.92,
            ),
            "road_published": self._complaint_defaults(
                category=Category.ROAD,
                status=ComplaintStatus.PUBLISHED,
                lat="56.951500",
                lon="24.113300",
                ai_verified=True,
                ai_confidence=0.88,
            ),
            "graffiti_published": self._complaint_defaults(
                category=Category.GRAFFITI,
                status=ComplaintStatus.PUBLISHED,
                lat="56.947900",
                lon="24.117200",
            ),
            "road_in_progress": self._complaint_defaults(
                category=Category.ROAD,
                status=ComplaintStatus.IN_PROGRESS,
                lat="56.955000",
                lon="24.121000",
            ),
            "trash_resolved": self._complaint_defaults(
                category=Category.TRASH,
                status=ComplaintStatus.RESOLVED,
                lat="56.944500",
                lon="24.101400",
            ),
        }

        complaints = {}
        for key, defaults in specs.items():
            complaint, created = Complaint.objects.update_or_create(
                cell_id=defaults["cell_id"],
                category=defaults["category"],
                defaults=defaults,
            )
            self._count(counters, "Complaint", created)
            complaints[key] = complaint
        return complaints

    def _seed_stack_reports(
        self,
        users: dict[str, Any],
        complaints: dict[str, Complaint],
        counters: dict[str, dict[str, int]],
    ) -> None:
        specs = (
            (complaints["trash_published"], users[UserLevel.ACTIVE], "Подтверждаю, мусор всё ещё на месте."),
            (complaints["trash_published"], users[UserLevel.TRUSTED], "Проблема актуальна."),
            (complaints["road_published"], users[UserLevel.TRUSTED], "Опасная яма на дороге."),
            (complaints["road_in_progress"], users[UserLevel.MODERATOR], "Работы начаты."),
            (complaints["trash_resolved"], users[UserLevel.ACTIVE], "Было убрано после обращения."),
        )
        for complaint, user, text in specs:
            _, created = StackReport.objects.update_or_create(
                complaint=complaint,
                user=user,
                defaults={"text": text},
            )
            self._count(counters, "StackReport", created)

    def _seed_incoming_reports(
        self,
        users: dict[str, Any],
        counters: dict[str, dict[str, int]],
    ) -> dict[str, IncomingReport]:
        specs = {
            "pending_ai": {
                "user": users[UserLevel.NEWBIE],
                "declared_category": Category.TRASH,
                "text": "Переполненная урна у остановки.",
                "lat": "56.950500",
                "lon": "24.110100",
                "status": IncomingStatus.PENDING_AI,
            },
            "needs_moderation": {
                "user": users[UserLevel.ACTIVE],
                "declared_category": Category.ROAD,
                "text": "Провал плитки на тротуаре.",
                "lat": "56.952200",
                "lon": "24.116700",
                "status": IncomingStatus.NEEDS_MODERATION,
                "ai_pred_category": Category.ROAD,
                "ai_confidence": 0.54,
            },
            "rejected": {
                "user": users[UserLevel.NEWBIE],
                "declared_category": Category.GRAFFITI,
                "text": "Не городская территория.",
                "lat": "56.946700",
                "lon": "24.099900",
                "status": IncomingStatus.REJECTED,
                "ai_pred_category": Category.GRAFFITI,
                "ai_confidence": 0.41,
            },
            "processed": {
                "user": users[UserLevel.TRUSTED],
                "declared_category": Category.TRASH,
                "text": "Мусор у входа в парк.",
                "lat": "56.948800",
                "lon": "24.108300",
                "status": IncomingStatus.PROCESSED,
                "ai_pred_category": Category.TRASH,
                "ai_confidence": 0.95,
            },
        }

        incoming_reports = {}
        for key, defaults in specs.items():
            defaults = {
                **defaults,
                "cell_id": make_cell_id(defaults["lat"], defaults["lon"]),
            }
            incoming, created = IncomingReport.objects.update_or_create(
                user=defaults["user"],
                text=defaults["text"],
                defaults=defaults,
            )
            self._count(counters, "IncomingReport", created)
            incoming_reports[key] = incoming
        return incoming_reports

    def _seed_importance_votes(
        self,
        users: dict[str, Any],
        complaints: dict[str, Complaint],
        counters: dict[str, dict[str, int]],
    ) -> None:
        specs = (
            (complaints["trash_published"], users[UserLevel.ACTIVE], ComplaintImportance.HIGH),
            (complaints["road_published"], users[UserLevel.TRUSTED], ComplaintImportance.HIGH),
            (complaints["graffiti_published"], users[UserLevel.ACTIVE], ComplaintImportance.NORMAL),
            (complaints["road_in_progress"], users[UserLevel.MODERATOR], ComplaintImportance.HIGH),
        )
        for complaint, user, importance in specs:
            _, created = ComplaintImportanceVote.objects.update_or_create(
                complaint=complaint,
                user=user,
                defaults={
                    "importance": importance,
                    "weight": IMPORTANCE_WEIGHTS[importance],
                },
            )
            self._count(counters, "ComplaintImportanceVote", created)

    def _seed_rating_events(
        self,
        users: dict[str, Any],
        complaints: dict[str, Complaint],
        incoming_reports: dict[str, IncomingReport],
        counters: dict[str, dict[str, int]],
    ) -> None:
        specs = (
            {
                "user": users[UserLevel.TRUSTED],
                "delta": 5,
                "reason": UserRatingReason.AI_APPROVED_REPORT,
                "incoming_report": incoming_reports["processed"],
            },
            {
                "user": users[UserLevel.ACTIVE],
                "delta": 5,
                "reason": UserRatingReason.MODERATOR_APPROVED_REPORT,
                "incoming_report": incoming_reports["needs_moderation"],
            },
            {
                "user": users[UserLevel.NEWBIE],
                "delta": -3,
                "reason": UserRatingReason.MODERATOR_REJECTED_REPORT,
                "incoming_report": incoming_reports["rejected"],
            },
            {
                "user": users[UserLevel.ACTIVE],
                "delta": 1,
                "reason": UserRatingReason.CONFIRMED_COMPLAINT,
                "complaint": complaints["trash_published"],
            },
            {
                "user": users[UserLevel.MODERATOR],
                "delta": 0,
                "reason": UserRatingReason.OTHER,
                "complaint": complaints["road_in_progress"],
            },
        )

        for spec in specs:
            lookup = {
                "user": spec["user"],
                "reason": spec["reason"],
            }
            if spec.get("incoming_report") is not None:
                lookup["incoming_report"] = spec["incoming_report"]
            if spec.get("complaint") is not None:
                lookup["complaint"] = spec["complaint"]

            _, created = UserRatingEvent.objects.update_or_create(
                **lookup,
                defaults={
                    "delta": spec["delta"],
                    "complaint": spec.get("complaint"),
                    "incoming_report": spec.get("incoming_report"),
                },
            )
            self._count(counters, "UserRatingEvent", created)
