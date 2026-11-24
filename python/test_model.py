"""用解析几何和固定种子检验模型及优化器的关键性质。"""
import unittest
from dataclasses import replace
import numpy as np
from bedroom_ga import (ROOMS, GAConfig, FURNITURE, intersection_area,
                        rectangle_gap, sample_population, decode, evaluate, optimize,
                        room_spec, solution_details)
from verify_results import verify_desk_chair
from window_layout import MARGIN, WIDTHS, decode_window, window_metrics


class ModelTests(unittest.TestCase):
    def test_known_rectangle_geometry(self):
        a = np.array([0., 0., 2., 2.])
        b = np.array([1., 1., 3., 4.])
        self.assertAlmostEqual(float(intersection_area(a, b)), 1.)
        self.assertAlmostEqual(float(rectangle_gap(a, np.array([3., 2., 4., 3.]))), 1.)
        self.assertEqual(float(intersection_area(a, np.array([2., 0., 3., 1.]))), 0.)

    def test_rotation_and_boundaries(self):
        room = ROOMS["standard"]
        genes = np.zeros((2, len(FURNITURE), 3))
        genes[1] = 1.
        boxes = decode(genes, room)
        np.testing.assert_allclose(boxes[0, 0], [0., 0., 1.5, 2.])
        np.testing.assert_allclose(boxes[1, 0], [3., 2.5, 5., 4.])
        random_boxes = decode(sample_population(np.random.default_rng(0), 1000), room)
        self.assertTrue(np.all(random_boxes[:, :, :2] >= 0))
        self.assertTrue(np.all(random_boxes[:, :, 2:] <= [5, 4]))

    def test_known_feasible_layout_and_overlap(self):
        # 独立手工构造，仅用于验证；不注入任何实验的初始种群。
        room = ROOMS["standard"]
        lower = np.array([[2., 1.8], [3.2, 0.], [3.8, 3.4],
                          [4.15, 2.8], [1.45, 2.5], [0., 3.65]])
        sizes = np.array([(f.width, f.depth) for f in FURNITURE])
        genes = np.zeros((len(FURNITURE), 3))
        genes[:, :2] = lower / (np.array([5., 4.]) - sizes)
        # 书桌靠右上角，椅子位于书桌下方并朝上。
        genes[2, :2] = 1
        genes[3] = [0, 0, 1]
        np.testing.assert_allclose(decode(genes, room)[:, :2], lower)
        detail = evaluate(genes, room)
        self.assertTrue(detail["feasible"][0])
        self.assertLessEqual(detail["cost"][0], 1.)
        bad = genes.copy()
        bad[4, :2] = lower[0] / (np.array([5., 4.]) - sizes[4])
        detail_bad = evaluate(bad, room)
        self.assertFalse(detail_bad["feasible"][0])
        self.assertGreater(detail_bad["cost"][0], 2.)
        self.assertAlmostEqual(detail_bad["overlap_m2"][0], .25)

    def test_door_and_passage_areas(self):
        zone = ROOMS["standard"].zones
        item = np.array([.25, .5, .75, 1.5])
        np.testing.assert_allclose(intersection_area(item, zone), [.25, .25])

    def test_desk_chair_alignment_at_room_edges(self):
        for key in ("standard", "compact"):
            room = ROOMS[key]
            directions = set()
            for edge in (0, 1):
                for rotate in (0, 1):
                    for reverse in (0, 1):
                        genes = np.full((len(FURNITURE), 3), edge, dtype=float)
                        genes[2, 2] = rotate
                        genes[3, 2] = reverse
                        result = solution_details(genes, room)
                        verify_desk_chair(room_spec(room), result)
                        directions.add(tuple(result["furniture"][2]["front_xy"]))
                        boxes = np.asarray([item["box_m"] for item in result["furniture"]])
                        self.assertTrue(np.all(boxes[:, :2] >= -1e-9))
                        self.assertTrue(np.all(boxes[:, 2:] <= [room.width + 1e-9, room.height + 1e-9]))
            self.assertEqual(len(directions), 4)

    def test_budget_shared_initial_and_reproducibility(self):
        config = GAConfig(population=16, elite=2, generations=5)
        room = ROOMS["standard"]
        a = optimize(room, config, 3, "ga")
        b = optimize(room, config, 3, "ga")
        c = optimize(room, config, 3, "random")
        self.assertEqual(a["best"], b["best"])
        self.assertEqual(a["history"], b["history"])
        self.assertEqual(a["initial"], c["initial"])
        self.assertEqual(a["evaluations"], 16+5*14)
        self.assertEqual(a["evaluations"], c["evaluations"])
        self.assertTrue(np.all(np.diff([h["cost"] for h in a["history"]]) <= 0))

    def test_size_pairs_share_rules_and_fit(self):
        self.assertEqual(len(ROOMS), 8)
        for kind in ("bedroom", "bathroom", "kitchen", "living"):
            large, small = [r for r in ROOMS.values() if r.kind == kind]
            self.assertAlmostEqual(small.width * small.height / (large.width * large.height), 2 / 3)
            self.assertAlmostEqual(large.width / large.height, small.width / small.height)
            self.assertEqual(large.furniture, small.furniture)
            np.testing.assert_array_equal(large.zones, small.zones)
            self.assertTrue(np.all(small.zones[:, 2:] <= [small.width, small.height]))
            self.assertTrue(all(max(f.width, f.depth) <= min(small.width, small.height)
                                for f in small.furniture))

    def test_all_room_types_use_common_search(self):
        config = GAConfig(population=16, elite=2, generations=5)
        for room in ROOMS.values():
            with self.subTest(room=room.key):
                runs = [optimize(room, config, 20, m)
                        for m in ("ga", "random", "ga_no_mutation")]
                for run in runs:
                    self.assertEqual(run["initial"], runs[0]["initial"])
                    self.assertEqual(run["evaluations"], 86)
                    self.assertEqual(len(run["best"]["furniture"]), len(room.furniture))
                    metrics = run["best"]["metrics"]
                    self.assertGreaterEqual(metrics["soft"], 0)
                    self.assertLessEqual(metrics["soft"], 1)
                    self.assertEqual(metrics["feasible"], metrics["violation_m2"] <= 1e-9)

    def test_functional_candidates_stay_in_bounds_at_gene_extremes(self):
        for key in ("kitchen_compact", "living_compact"):
            room = replace(ROOMS[key], functional=True)
            genes = np.ones((4, len(room.furniture), 3))
            genes[:, 0, 0] = [0, .25, .50, .75]
            boxes, _, zones, detail = decode(genes, room, with_function=True)
            for rectangles in (boxes, zones):
                self.assertTrue(np.all(rectangles[..., :2] >= -1e-9))
                self.assertTrue(np.all(rectangles[..., 2:] <= [room.width+1e-9, room.height+1e-9]))
            if room.kind == "living":
                self.assertTrue(np.all(detail["table_tv_gap_m"]-detail["sofa_table_gap_m"] >= .15-1e-9))

    def test_window_can_sweep_both_walls_up_to_the_corner_margin(self):
        for room in ROOMS.values():
            genes = np.zeros((4, len(room.furniture)+1, 3))
            genes[:, -1, 0] = [0, 1, 0, 1]
            genes[:, -1, 2] = [0, 0, 1, 1]
            right, start, end = decode_window(genes, room)
            np.testing.assert_array_equal(right, [False, False, True, True])
            np.testing.assert_allclose(start[[0, 2]], [[MARGIN, room.height], [room.width, MARGIN]])
            np.testing.assert_allclose(end[[1, 3]], [[room.width-MARGIN, room.height],
                                                     [room.width, room.height-MARGIN]])
            np.testing.assert_allclose(np.linalg.norm(end-start, axis=1), WIDTHS[room.kind])

    def test_living_window_cost_depends_on_sofa_facing_axis(self):
        room = replace(ROOMS["living_standard"], functional=True)
        genes = np.zeros((4, len(room.furniture)+1, 3))
        genes[:, 0, 0] = [0, 0, .25, .25]
        genes[:, -1, 2] = [0, 1, 0, 1]
        boxes, fronts, _, _ = decode(genes, room, with_function=True)
        result = window_metrics(genes, room, boxes, fronts)
        np.testing.assert_array_equal(result["window"], [1, 0, 0, 1])

if __name__ == "__main__":
    unittest.main(verbosity=2)
