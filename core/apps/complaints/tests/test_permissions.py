from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.apps.accounts.models import UserLevel
from core.apps.complaints.models import Category, Complaint, ComplaintImportance, ComplaintStatus, IncomingReport, IncomingStatus
from core.apps.moderation.models import Decision


User = get_user_model()


class ComplaintPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.newbie = self.create_user_with_level("newbie", UserLevel.NEWBIE)
        self.active = self.create_user_with_level("active", UserLevel.ACTIVE)
        self.trusted = self.create_user_with_level("trusted", UserLevel.TRUSTED)
        self.moderator = self.create_user_with_level("moderator", UserLevel.MODERATOR)

    def create_user_with_level(self, username: str, level: str):
        user = User.objects.create_user(username=username, password="pass")
        user.profile.level = level
        user.profile.is_level_manual = True
        user.profile.save()
        return user

    def create_complaint(self, status: str = ComplaintStatus.PUBLISHED) -> Complaint:
        return Complaint.objects.create(
            category=Category.TRASH,
            status=status,
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            stack_count=0,
            priority_score=0,
        )

    def create_incoming(self) -> IncomingReport:
        return IncomingReport.objects.create(
            user=self.active,
            declared_category=Category.TRASH,
            text="Проблема во дворе",
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            status=IncomingStatus.NEEDS_MODERATION,
        )

    def report_payload(self) -> dict[str, str]:
        return {
            "declared_category": Category.TRASH,
            "text": "Проблема во дворе",
            "lat": "55.751244",
            "lon": "37.618423",
        }

    def test_anonymous_cannot_create_report(self):
        response = self.client.post("/api/v1/reports/", self.report_payload(), format="json")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_can_create_report(self):
        self.client.force_authenticate(user=self.active)

        with patch("core.apps.complaints.views.run_ai_check.delay") as delay_mock:
            response = self.client.post("/api/v1/reports/", self.report_payload(), format="json")

        self.assertEqual(response.status_code, 201)
        delay_mock.assert_called_once()

    def test_newbie_cannot_confirm_complaint(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.newbie)

        response = self.client.post(f"/api/v1/complaints/{complaint.id}/confirm/", {}, format="json")

        self.assertEqual(response.status_code, 403)

    def test_active_can_confirm_complaint(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.active)

        response = self.client.post(f"/api/v1/complaints/{complaint.id}/confirm/", {}, format="json")

        self.assertEqual(response.status_code, 201)

    def test_trusted_can_confirm_complaint(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.trusted)

        response = self.client.post(f"/api/v1/complaints/{complaint.id}/confirm/", {}, format="json")

        self.assertEqual(response.status_code, 201)

    def test_moderator_can_confirm_complaint(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(f"/api/v1/complaints/{complaint.id}/confirm/", {}, format="json")

        self.assertEqual(response.status_code, 201)

    def test_repeated_confirm_is_forbidden(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.active)

        first_response = self.client.post(f"/api/v1/complaints/{complaint.id}/confirm/", {}, format="json")
        second_response = self.client.post(f"/api/v1/complaints/{complaint.id}/confirm/", {}, format="json")

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 400)

    def test_newbie_cannot_set_importance(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.newbie)

        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/set-importance/",
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_active_can_set_importance(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.active)

        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/set-importance/",
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_trusted_can_set_importance(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.trusted)

        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/set-importance/",
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_moderator_can_set_importance(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/set-importance/",
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_get_moderation_queue(self):
        self.client.force_authenticate(user=self.active)

        response = self.client.get("/api/v1/moderation/incoming/")

        self.assertEqual(response.status_code, 403)

    def test_moderator_can_get_moderation_queue(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.get("/api/v1/moderation/incoming/")

        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_post_moderation_decision(self):
        incoming = self.create_incoming()
        self.client.force_authenticate(user=self.active)

        response = self.client.post(
            f"/api/v1/moderation/incoming/{incoming.id}/decision/",
            {"decision": Decision.APPROVE},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_moderator_can_post_moderation_decision(self):
        incoming = self.create_incoming()
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            f"/api/v1/moderation/incoming/{incoming.id}/decision/",
            {"decision": Decision.APPROVE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_ordinary_user_cannot_change_complaint_status(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.active)

        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/status/",
            {"status": ComplaintStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_moderator_can_change_complaint_status(self):
        complaint = self.create_complaint()
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/status/",
            {"status": ComplaintStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
