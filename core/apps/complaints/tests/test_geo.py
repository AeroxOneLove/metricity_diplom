from __future__ import annotations

from django.test import SimpleTestCase

from core.apps.complaints.services.geo import haversine_m, make_cell_id, neighbor_cells


class GeoServiceTests(SimpleTestCase):
    def test_make_cell_id_same_coordinates_returns_same_cell_id(self):
        first_cell_id = make_cell_id(lat="55.751244", lon="37.618423")
        second_cell_id = make_cell_id(lat="55.751244", lon="37.618423")

        self.assertEqual(first_cell_id, second_cell_id)

    def test_neighbor_cells_returns_nine_ids(self):
        cell_id = make_cell_id(lat="55.751244", lon="37.618423")

        neighbors = neighbor_cells(cell_id)

        self.assertEqual(len(neighbors), 9)

    def test_neighbor_cells_includes_original_cell(self):
        cell_id = make_cell_id(lat="55.751244", lon="37.618423")

        neighbors = neighbor_cells(cell_id)

        self.assertIn(cell_id, neighbors)

    def test_neighbor_cells_has_no_duplicates(self):
        cell_id = make_cell_id(lat="55.751244", lon="37.618423")

        neighbors = neighbor_cells(cell_id)

        self.assertEqual(len(neighbors), len(set(neighbors)))

    def test_haversine_same_points_is_about_zero(self):
        distance = haversine_m("55.751244", "37.618423", "55.751244", "37.618423")

        self.assertAlmostEqual(distance, 0, places=6)

    def test_haversine_close_different_points_is_positive(self):
        distance = haversine_m("55.751244", "37.618423", "55.751245", "37.618424")

        self.assertGreater(distance, 0)
