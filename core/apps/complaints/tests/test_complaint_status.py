from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.apps.accounts.models import UserLevel
from core.apps.complaints.models import Category, Complaint, ComplaintStatus


User = get_user_model()


class ComplaintStatusUpdateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.moderator = User.objects.create_user(username="moderator", password="pass")
        self.moderator.profile.level = UserLevel.MODERATOR
        self.moderator.profile.is_level_manual = True
        self.moderator.profile.save()

        self.user = User.objects.create_user(username="user", password="pass")

    def _create_complaint(self, status: str) -> Complaint:
        return Complaint.objects.create(
            category=Category.TRASH,
            status=status,
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            stack_count=1,
            priority_score=1,
        )

    def _url(self, complaint: Complaint) -> str:
        return f"/api/v1/complaints/{complaint.id}/status/"

    def test_moderator_can_change_published_to_in_progress(self):
        complaint = self._create_complaint(ComplaintStatus.PUBLISHED)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(complaint),
            {"status": ComplaintStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"id": complaint.id, "status": ComplaintStatus.IN_PROGRESS},
        )
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.IN_PROGRESS)

    def test_moderator_can_change_in_progress_to_resolved(self):
        complaint = self._create_complaint(ComplaintStatus.IN_PROGRESS)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(complaint),
            {"status": ComplaintStatus.RESOLVED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.RESOLVED)

    def test_regular_user_cannot_change_status(self):
        complaint = self._create_complaint(ComplaintStatus.PUBLISHED)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self._url(complaint),
            {"status": ComplaintStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.PUBLISHED)

    def test_anonymous_user_cannot_change_status(self):
        complaint = self._create_complaint(ComplaintStatus.PUBLISHED)

        response = self.client.post(
            self._url(complaint),
            {"status": ComplaintStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.PUBLISHED)

    def test_forbidden_transition_returns_400(self):
        complaint = self._create_complaint(ComplaintStatus.RESOLVED)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(complaint),
            {"status": ComplaintStatus.PUBLISHED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.RESOLVED)

    def test_unknown_status_returns_400(self):
        complaint = self._create_complaint(ComplaintStatus.PUBLISHED)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(complaint),
            {"status": "UNKNOWN"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, ComplaintStatus.PUBLISHED)
