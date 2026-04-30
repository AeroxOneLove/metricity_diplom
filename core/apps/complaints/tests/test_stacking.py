from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.apps.complaints.models import Category, Complaint, ComplaintStatus, IncomingReport, IncomingStatus, StackReport
from core.apps.complaints.services.geo import make_cell_id
from core.apps.complaints.services.stacking import attach_to_master


User = get_user_model()


class AttachToMasterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

    def _create_complaint(
        self,
        *,
        category: str = Category.TRASH,
        status: str = ComplaintStatus.PUBLISHED,
        lat: str = "55.751244",
        lon: str = "37.618423",
    ) -> Complaint:
        return Complaint.objects.create(
            category=category,
            status=status,
            lat=lat,
            lon=lon,
            cell_id=make_cell_id(lat, lon),
            stack_count=0,
            priority_score=0,
        )

    def _create_incoming(
        self,
        *,
        user=None,
        declared_category: str = Category.TRASH,
        lat: str = "55.751245",
        lon: str = "37.618424",
    ) -> IncomingReport:
        return IncomingReport.objects.create(
            user=user or self.user,
            declared_category=declared_category,
            text="Проблема во дворе",
            lat=lat,
            lon=lon,
            cell_id=make_cell_id(lat, lon),
            status=IncomingStatus.PROCESSED,
        )

    def test_same_category_nearby_attaches_to_existing_complaint(self):
        complaint = self._create_complaint()
        incoming = self._create_incoming()

        master = attach_to_master(incoming)

        self.assertEqual(master.id, complaint.id)
        self.assertEqual(Complaint.objects.count(), 1)
        self.assertTrue(StackReport.objects.filter(complaint=complaint, user=self.user).exists())
        complaint.refresh_from_db()
        self.assertEqual(complaint.stack_count, 1)

    def test_far_report_creates_new_complaint(self):
        existing_complaint = self._create_complaint()
        incoming = self._create_incoming(lat="55.761244", lon="37.628423")

        master = attach_to_master(incoming)

        self.assertNotEqual(master.id, existing_complaint.id)
        self.assertEqual(Complaint.objects.count(), 2)
        self.assertTrue(StackReport.objects.filter(complaint=master, user=self.user).exists())

    def test_different_category_nearby_creates_new_complaint(self):
        existing_complaint = self._create_complaint(category=Category.ROAD)
        incoming = self._create_incoming(declared_category=Category.TRASH)

        master = attach_to_master(incoming)

        self.assertNotEqual(master.id, existing_complaint.id)
        self.assertEqual(master.category, Category.TRASH)
        self.assertEqual(Complaint.objects.count(), 2)

    def test_resolved_complaint_is_not_used_for_stacking(self):
        resolved_complaint = self._create_complaint(status=ComplaintStatus.RESOLVED)
        incoming = self._create_incoming()

        master = attach_to_master(incoming)

        self.assertNotEqual(master.id, resolved_complaint.id)
        self.assertEqual(Complaint.objects.count(), 2)

    def test_rejected_complaint_is_not_used_for_stacking(self):
        rejected_complaint = self._create_complaint(status=ComplaintStatus.REJECTED)
        incoming = self._create_incoming()

        master = attach_to_master(incoming)

        self.assertNotEqual(master.id, rejected_complaint.id)
        self.assertEqual(Complaint.objects.count(), 2)

    def test_repeat_from_same_user_does_not_increase_stack_count(self):
        complaint = self._create_complaint()
        first_incoming = self._create_incoming()
        second_incoming = self._create_incoming()

        first_master = attach_to_master(first_incoming)
        second_master = attach_to_master(second_incoming)

        self.assertEqual(first_master.id, complaint.id)
        self.assertEqual(second_master.id, complaint.id)
        self.assertEqual(StackReport.objects.filter(complaint=complaint, user=self.user).count(), 1)
        complaint.refresh_from_db()
        self.assertEqual(complaint.stack_count, 1)
