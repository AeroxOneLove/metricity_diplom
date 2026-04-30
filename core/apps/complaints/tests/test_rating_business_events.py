from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.apps.accounts.models import UserLevel, UserRatingEvent, UserRatingReason
from core.apps.complaints.models import Category, Complaint, ComplaintStatus, IncomingReport, IncomingStatus
from core.apps.complaints.tasks import run_ai_check
from core.apps.moderation.models import Decision


User = get_user_model()


class RatingBusinessEventTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="user", password="pass")
        self.active_user = self._create_user_with_level("active", UserLevel.ACTIVE)
        self.moderator = self._create_user_with_level("moderator", UserLevel.MODERATOR)

    def _create_user_with_level(self, username: str, level: str):
        user = User.objects.create_user(username=username, password="pass")
        user.profile.level = level
        user.profile.is_level_manual = True
        user.profile.save()
        return user

    def _create_incoming(
        self,
        *,
        user=None,
        status: str = IncomingStatus.NEEDS_MODERATION,
    ) -> IncomingReport:
        return IncomingReport.objects.create(
            user=user or self.user,
            declared_category=Category.TRASH,
            text="Проблема во дворе",
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            status=status,
        )

    def _create_complaint(self) -> Complaint:
        return Complaint.objects.create(
            category=Category.TRASH,
            status=ComplaintStatus.PUBLISHED,
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            stack_count=0,
            priority_score=0,
        )

    def test_ai_approve_adds_rating(self):
        incoming = self._create_incoming(status=IncomingStatus.PENDING_AI)

        with patch(
            "core.apps.complaints.tasks._call_ml_service",
            return_value={"confidence": 0.95, "is_match": True, "pred_category": Category.TRASH},
        ):
            run_ai_check.run(incoming.id)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 5)
        self.assertTrue(
            UserRatingEvent.objects.filter(
                user=self.user,
                reason=UserRatingReason.AI_APPROVED_REPORT,
                incoming_report=incoming,
            ).exists()
        )

    def test_repeated_ai_task_does_not_add_second_rating(self):
        incoming = self._create_incoming(status=IncomingStatus.PENDING_AI)

        with patch(
            "core.apps.complaints.tasks._call_ml_service",
            return_value={"confidence": 0.95, "is_match": True, "pred_category": Category.TRASH},
        ) as ml_mock:
            run_ai_check.run(incoming.id)
            run_ai_check.run(incoming.id)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 5)
        self.assertEqual(
            UserRatingEvent.objects.filter(
                user=self.user,
                reason=UserRatingReason.AI_APPROVED_REPORT,
                incoming_report=incoming,
            ).count(),
            1,
        )
        self.assertEqual(ml_mock.call_count, 1)

    def test_moderation_approve_adds_rating(self):
        incoming = self._create_incoming()
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            f"/api/v1/moderation/incoming/{incoming.id}/decision/",
            {"decision": Decision.APPROVE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, 5)
        self.assertTrue(
            UserRatingEvent.objects.filter(
                user=self.user,
                reason=UserRatingReason.MODERATOR_APPROVED_REPORT,
                incoming_report=incoming,
            ).exists()
        )

    def test_moderation_reject_decreases_rating(self):
        incoming = self._create_incoming()
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            f"/api/v1/moderation/incoming/{incoming.id}/decision/",
            {"decision": Decision.REJECT, "reason": "Не обнаружена проблема"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.rating, -3)
        self.assertTrue(
            UserRatingEvent.objects.filter(
                user=self.user,
                reason=UserRatingReason.MODERATOR_REJECTED_REPORT,
                incoming_report=incoming,
            ).exists()
        )

    def test_confirm_adds_rating(self):
        complaint = self._create_complaint()
        self.client.force_authenticate(user=self.active_user)

        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.active_user.profile.refresh_from_db()
        self.assertEqual(self.active_user.profile.rating, 1)
        self.assertTrue(
            UserRatingEvent.objects.filter(
                user=self.active_user,
                reason=UserRatingReason.CONFIRMED_COMPLAINT,
                complaint=complaint,
            ).exists()
        )

    def test_repeated_confirm_does_not_add_second_rating(self):
        complaint = self._create_complaint()
        self.client.force_authenticate(user=self.active_user)

        first_response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/confirm/",
            {},
            format="json",
        )
        second_response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/confirm/",
            {},
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.active_user.profile.refresh_from_db()
        self.assertEqual(self.active_user.profile.rating, 1)
        self.assertEqual(
            UserRatingEvent.objects.filter(
                user=self.active_user,
                reason=UserRatingReason.CONFIRMED_COMPLAINT,
                complaint=complaint,
            ).count(),
            1,
        )
