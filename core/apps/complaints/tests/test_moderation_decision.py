from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.apps.accounts.models import UserLevel
from core.apps.complaints.models import Category, Complaint, ComplaintStatus, IncomingReport, IncomingStatus
from core.apps.moderation.models import Decision, ModerationDecision


User = get_user_model()


class ModerationDecisionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.moderator = User.objects.create_user(username="moderator", password="pass")
        self.moderator.profile.level = UserLevel.MODERATOR
        self.moderator.profile.is_level_manual = True
        self.moderator.profile.save()

        self.user = User.objects.create_user(username="user", password="pass")

    def _create_incoming(self, declared_category: str = Category.TRASH) -> IncomingReport:
        return IncomingReport.objects.create(
            user=self.user,
            declared_category=declared_category,
            text="Проблема во дворе",
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            status=IncomingStatus.NEEDS_MODERATION,
        )

    def _url(self, incoming: IncomingReport) -> str:
        return f"/api/v1/moderation/incoming/{incoming.id}/decision/"

    def test_approve_without_category_uses_declared_category(self):
        incoming = self._create_incoming(declared_category=Category.TRASH)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(incoming),
            {"decision": Decision.APPROVE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        complaint = Complaint.objects.get()
        decision = ModerationDecision.objects.get(incoming=incoming)
        self.assertEqual(complaint.category, Category.TRASH)
        self.assertEqual(decision.final_category, Category.TRASH)

    def test_approve_with_category_attaches_by_new_category(self):
        existing_complaint = Complaint.objects.create(
            category=Category.ROAD,
            status=ComplaintStatus.PUBLISHED,
            lat="55.751245",
            lon="37.618424",
            cell_id="55.751:37.618",
            stack_count=1,
            priority_score=1,
        )
        incoming = self._create_incoming(declared_category=Category.TRASH)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(incoming),
            {"decision": Decision.APPROVE, "category": Category.ROAD},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        existing_complaint.refresh_from_db()
        self.assertEqual(Complaint.objects.count(), 1)
        self.assertEqual(existing_complaint.stack_count, 2)
        self.assertEqual(response.data["complaint"]["id"], existing_complaint.id)

    def test_approve_with_category_does_not_change_declared_category(self):
        incoming = self._create_incoming(declared_category=Category.TRASH)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(incoming),
            {"decision": Decision.APPROVE, "category": Category.ROAD},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        incoming.refresh_from_db()
        self.assertEqual(incoming.declared_category, Category.TRASH)

    def test_reject_saves_reason(self):
        incoming = self._create_incoming()
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(incoming),
            {
                "decision": Decision.REJECT,
                "reason": "На фото не обнаружена проблема",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        decision = ModerationDecision.objects.get(incoming=incoming)
        self.assertEqual(decision.reason, "На фото не обнаружена проблема")
        self.assertEqual(decision.note, "На фото не обнаружена проблема")

    def test_approve_saves_final_category(self):
        incoming = self._create_incoming(declared_category=Category.TRASH)
        self.client.force_authenticate(user=self.moderator)

        response = self.client.post(
            self._url(incoming),
            {"decision": Decision.APPROVE, "category": Category.ROAD},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        decision = ModerationDecision.objects.get(incoming=incoming)
        self.assertEqual(decision.final_category, Category.ROAD)

    def test_only_moderator_can_make_decision(self):
        incoming = self._create_incoming()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self._url(incoming),
            {"decision": Decision.APPROVE},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ModerationDecision.objects.filter(incoming=incoming).exists())
