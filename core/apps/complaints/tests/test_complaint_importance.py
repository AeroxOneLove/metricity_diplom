from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.apps.accounts.models import UserLevel
from core.apps.complaints.models import (
    Category,
    Complaint,
    ComplaintImportance,
    ComplaintImportanceVote,
    ComplaintStatus,
    StackReport,
)


User = get_user_model()


class ComplaintImportanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.complaint = Complaint.objects.create(
            category=Category.TRASH,
            status=ComplaintStatus.PUBLISHED,
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            stack_count=0,
            priority_score=0,
        )

        self.active = self._create_user_with_level("active", UserLevel.ACTIVE)
        self.newbie = self._create_user_with_level("newbie", UserLevel.NEWBIE)
        self.trusted = self._create_user_with_level("trusted", UserLevel.TRUSTED)
        self.moderator = self._create_user_with_level("moderator", UserLevel.MODERATOR)

    def _create_user_with_level(self, username: str, level: str):
        user = User.objects.create_user(username=username, password="pass")
        user.profile.level = level
        user.profile.is_level_manual = True
        user.profile.save()
        return user

    def _url(self) -> str:
        return f"/api/v1/complaints/{self.complaint.id}/set-importance/"

    def test_active_can_set_importance(self):
        self.client.force_authenticate(user=self.active)

        response = self.client.post(
            self._url(),
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["complaint_id"], self.complaint.id)
        self.assertEqual(response.data["importance"], ComplaintImportance.HIGH)
        self.assertEqual(ComplaintImportanceVote.objects.count(), 1)

    def test_newbie_cannot_set_importance(self):
        self.client.force_authenticate(user=self.newbie)

        response = self.client.post(
            self._url(),
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ComplaintImportanceVote.objects.count(), 0)

    def test_trusted_can_set_importance(self):
        self.client.force_authenticate(user=self.trusted)

        response = self.client.post(
            self._url(),
            {"importance": ComplaintImportance.NORMAL},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ComplaintImportanceVote.objects.count(), 1)

    def test_moderator_can_set_importance(self):
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(),
            {"importance": ComplaintImportance.LOW},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ComplaintImportanceVote.objects.count(), 1)

    def test_repeated_post_updates_existing_vote(self):
        self.client.force_authenticate(user=self.active)

        first_response = self.client.post(
            self._url(),
            {"importance": ComplaintImportance.LOW},
            format="json",
        )
        second_response = self.client.post(
            self._url(),
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(ComplaintImportanceVote.objects.count(), 1)
        vote = ComplaintImportanceVote.objects.get()
        self.assertEqual(vote.importance, ComplaintImportance.HIGH)
        self.assertEqual(vote.weight, 3)

    def test_priority_score_changes(self):
        StackReport.objects.create(complaint=self.complaint, user=self.active)
        self.client.force_authenticate(user=self.active)

        response = self.client.post(
            self._url(),
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.priority_score, 4)
        self.assertEqual(response.data["priority_score"], 4.0)

    def test_invalid_importance_returns_400(self):
        self.client.force_authenticate(user=self.active)

        response = self.client.post(
            self._url(),
            {"importance": "CRITICAL"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("importance", response.data)
