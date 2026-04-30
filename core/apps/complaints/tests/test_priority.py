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
from core.apps.complaints.services import confirm_complaint
from core.apps.complaints.services.priority import recalculate_priority_score


User = get_user_model()


class PriorityScoreTests(TestCase):
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
        self.active = self._create_user("active", UserLevel.ACTIVE)
        self.trusted = self._create_user("trusted", UserLevel.TRUSTED)
        self.moderator = self._create_user("moderator", UserLevel.MODERATOR)

    def _create_user(self, username: str, level: str):
        user = User.objects.create_user(username=username, password="pass")
        user.profile.level = level
        user.profile.is_level_manual = True
        user.profile.save()
        return user

    def _importance_url(self) -> str:
        return f"/api/v1/complaints/{self.complaint.id}/set-importance/"

    def test_without_trusted_and_importance_priority_score_equals_stack_count(self):
        StackReport.objects.create(complaint=self.complaint, user=self.active)

        recalculate_priority_score(self.complaint)

        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.stack_count, 1)
        self.assertEqual(self.complaint.priority_score, 1)

    def test_trusted_stack_report_adds_bonus(self):
        StackReport.objects.create(complaint=self.complaint, user=self.trusted)

        recalculate_priority_score(self.complaint)

        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.stack_count, 1)
        self.assertEqual(self.complaint.priority_score, 3)

    def test_moderator_stack_report_adds_bonus(self):
        StackReport.objects.create(complaint=self.complaint, user=self.moderator)

        recalculate_priority_score(self.complaint)

        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.stack_count, 1)
        self.assertEqual(self.complaint.priority_score, 3)

    def test_importance_votes_are_added_to_score(self):
        StackReport.objects.create(complaint=self.complaint, user=self.active)
        ComplaintImportanceVote.objects.create(
            complaint=self.complaint,
            user=self.trusted,
            importance=ComplaintImportance.HIGH,
            weight=3,
        )

        recalculate_priority_score(self.complaint)

        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.priority_score, 4)

    def test_confirm_recalculates_score(self):
        updated_complaint, created = confirm_complaint(
            complaint=self.complaint,
            user_id=self.active.id,
        )

        self.assertTrue(created)
        updated_complaint.refresh_from_db()
        self.assertEqual(updated_complaint.stack_count, 1)
        self.assertEqual(updated_complaint.priority_score, 1)

    def test_set_importance_recalculates_score(self):
        StackReport.objects.create(complaint=self.complaint, user=self.active)
        self.client.force_authenticate(user=self.active)

        response = self.client.post(
            self._importance_url(),
            {"importance": ComplaintImportance.HIGH},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.stack_count, 1)
        self.assertEqual(self.complaint.priority_score, 4)

    def test_repeated_confirm_does_not_increase_score(self):
        first_complaint, first_created = confirm_complaint(
            complaint=self.complaint,
            user_id=self.active.id,
        )
        second_complaint, second_created = confirm_complaint(
            complaint=first_complaint,
            user_id=self.active.id,
        )

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        second_complaint.refresh_from_db()
        self.assertEqual(second_complaint.stack_count, 1)
        self.assertEqual(second_complaint.priority_score, 1)
