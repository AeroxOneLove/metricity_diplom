from __future__ import annotations

import json
from unittest.mock import patch
from urllib import error

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.apps.accounts.models import UserRatingEvent, UserRatingReason
from core.apps.complaints.models import Category, Complaint, IncomingReport, IncomingStatus
from core.apps.complaints.tasks import run_ai_check


User = get_user_model()


class RunAiCheckTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

    def _create_incoming(self, status: str = IncomingStatus.PENDING_AI) -> IncomingReport:
        return IncomingReport.objects.create(
            user=self.user,
            declared_category=Category.TRASH,
            text="Проблема во дворе",
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            status=status,
        )

    def test_successful_ml_response_processes_report(self):
        incoming = self._create_incoming()

        with patch(
            "core.apps.complaints.tasks._call_ml_service",
            return_value={"confidence": 0.95, "is_match": True, "pred_category": Category.TRASH},
        ):
            run_ai_check.run(incoming.id)

        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingStatus.PROCESSED)
        self.assertEqual(incoming.ai_pred_category, Category.TRASH)
        self.assertEqual(incoming.ai_confidence, 0.95)
        self.assertEqual(Complaint.objects.count(), 1)
        self.assertEqual(UserRatingEvent.objects.filter(reason=UserRatingReason.AI_APPROVED_REPORT).count(), 1)

    def test_low_confidence_sends_report_to_moderation(self):
        incoming = self._create_incoming()

        with patch(
            "core.apps.complaints.tasks._call_ml_service",
            return_value={"confidence": 0.2, "is_match": True, "pred_category": Category.TRASH},
        ):
            run_ai_check.run(incoming.id)

        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingStatus.NEEDS_MODERATION)
        self.assertEqual(incoming.ai_pred_category, Category.TRASH)
        self.assertEqual(incoming.ai_confidence, 0.2)
        self.assertEqual(Complaint.objects.count(), 0)
        self.assertEqual(UserRatingEvent.objects.count(), 0)

    def test_ml_exception_sends_report_to_moderation(self):
        incoming = self._create_incoming()

        with patch(
            "core.apps.complaints.tasks._call_ml_service",
            side_effect=error.URLError("ML unavailable"),
        ):
            run_ai_check.run(incoming.id)

        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingStatus.NEEDS_MODERATION)
        self.assertIsNone(incoming.ai_pred_category)
        self.assertIsNone(incoming.ai_confidence)

    def test_bad_json_sends_report_to_moderation(self):
        incoming = self._create_incoming()

        with patch(
            "core.apps.complaints.tasks._call_ml_service",
            side_effect=json.JSONDecodeError("bad json", "not-json", 0),
        ):
            run_ai_check.run(incoming.id)

        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingStatus.NEEDS_MODERATION)
        self.assertIsNone(incoming.ai_pred_category)
        self.assertIsNone(incoming.ai_confidence)

    def test_repeated_task_for_processed_does_nothing(self):
        incoming = self._create_incoming(status=IncomingStatus.PROCESSED)
        incoming.ai_pred_category = Category.ROAD
        incoming.ai_confidence = 0.91
        incoming.save(update_fields=["ai_pred_category", "ai_confidence", "updated_at"])

        with patch("core.apps.complaints.tasks._call_ml_service") as ml_mock:
            run_ai_check.run(incoming.id)

        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingStatus.PROCESSED)
        self.assertEqual(incoming.ai_pred_category, Category.ROAD)
        self.assertEqual(incoming.ai_confidence, 0.91)
        self.assertEqual(Complaint.objects.count(), 0)
        ml_mock.assert_not_called()

    def test_repeated_task_for_rejected_does_nothing(self):
        incoming = self._create_incoming(status=IncomingStatus.REJECTED)
        incoming.ai_pred_category = Category.ROAD
        incoming.ai_confidence = 0.91
        incoming.save(update_fields=["ai_pred_category", "ai_confidence", "updated_at"])

        with patch("core.apps.complaints.tasks._call_ml_service") as ml_mock:
            run_ai_check.run(incoming.id)

        incoming.refresh_from_db()
        self.assertEqual(incoming.status, IncomingStatus.REJECTED)
        self.assertEqual(incoming.ai_pred_category, Category.ROAD)
        self.assertEqual(incoming.ai_confidence, 0.91)
        self.assertEqual(Complaint.objects.count(), 0)
        ml_mock.assert_not_called()
