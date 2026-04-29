from __future__ import annotations

from django.test import TestCase
from rest_framework.test import APIClient

from core.apps.complaints.models import Category, Complaint, ComplaintStatus


class ComplaintListTests(TestCase):
    url = "/api/v1/complaints/"

    @classmethod
    def setUpTestData(cls):
        cls.trash = Complaint.objects.create(
            category=Category.TRASH,
            status=ComplaintStatus.PUBLISHED,
            lat="55.751244",
            lon="37.618423",
            cell_id="55.751:37.618",
            stack_count=3,
            priority_score=3,
        )
        cls.road = Complaint.objects.create(
            category=Category.ROAD,
            status=ComplaintStatus.IN_PROGRESS,
            lat="55.755800",
            lon="37.617300",
            cell_id="55.756:37.617",
            stack_count=7,
            priority_score=7,
        )
        cls.graffiti = Complaint.objects.create(
            category=Category.GRAFFITI,
            status=ComplaintStatus.RESOLVED,
            lat="59.938630",
            lon="30.314130",
            cell_id="59.939:30.314",
            stack_count=1,
            priority_score=1,
        )

    def setUp(self):
        self.client = APIClient()

    def _result_ids(self, response) -> list[int]:
        return [item["id"] for item in response.data["results"]]

    def test_list_without_filters(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            set(response.data["results"][0].keys()),
            {"id", "lat", "lon", "category", "status", "priority_score"},
        )

    def test_bbox_filter(self):
        response = self.client.get(
            self.url,
            {
                "minLat": "55.70",
                "maxLat": "55.80",
                "minLon": "37.60",
                "maxLon": "37.70",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(self._result_ids(response)), {self.trash.id, self.road.id})

    def test_partial_bbox_returns_400(self):
        response = self.client.get(
            self.url,
            {
                "minLat": "55.70",
                "maxLat": "55.80",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("bbox", response.data)

    def test_invalid_bbox_returns_400(self):
        response = self.client.get(
            self.url,
            {
                "minLat": "not-a-float",
                "maxLat": "55.80",
                "minLon": "37.60",
                "maxLon": "37.70",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("minLat", response.data)

    def test_category_filter(self):
        response = self.client.get(self.url, {"category": Category.ROAD})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._result_ids(response), [self.road.id])

    def test_status_filter(self):
        response = self.client.get(self.url, {"status": ComplaintStatus.RESOLVED})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._result_ids(response), [self.graffiti.id])

    def test_allowed_ordering(self):
        response = self.client.get(self.url, {"ordering": "stack_count"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._result_ids(response),
            [self.graffiti.id, self.trash.id, self.road.id],
        )

    def test_forbidden_ordering_returns_400(self):
        response = self.client.get(self.url, {"ordering": "category"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("ordering", response.data)

    def test_page_size_pagination(self):
        response = self.client.get(self.url, {"page_size": "2", "ordering": "created_at"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])
