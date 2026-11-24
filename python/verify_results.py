"""审计全部已保存结果。几何校验直接使用导出的矩形，不调用优化器评分函数。"""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics


def area_intersection(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


def verify_window(room, spec, solution):
    window = solution["window"]
    rules = spec["window"]
    points = window["endpoints_m"]
    center = tuple(statistics.mean(coords) for coords in zip(*points, strict=True))
    assert all(math.isclose(actual, expected, abs_tol=1e-9)
               for actual, expected in zip(window["center_m"], center, strict=True))
    assert window["wall"] in rules["walls"] and window["wall"] in {"opposite", "right"}
    right = window["wall"] == "right"
    along, normal = (1, 0) if right else (0, 1)
    limits = (room["width"], room["height"])
    margin = rules["corner_margin_m"]
    assert all(math.isclose(p[normal], limits[normal], abs_tol=1e-9) for p in points)
    start, end = [p[along] for p in points]
    assert margin - 1e-9 <= start < end <= limits[along] - margin + 1e-9
    assert math.isclose(end - start, rules["width_m"], abs_tol=1e-9)

    items = solution["furniture"]
    target = next(item for item in items if item["name"] == rules["target"])
    metrics = solution["metrics"]
    if rules["rule"] == "sofa_side_wall":
        front = target["front_xy"]
        side = front[normal] == 0
        assert metrics["window_on_sofa_side"] == side
        window_cost = float(not side)
    else:
        assert rules["rule"] == "center_distance"
        a, b, c, d = target["box_m"]
        distance = math.dist(center, ((a+c)/2, (b+d)/2))
        assert math.isclose(metrics["window_distance_m"], distance, abs_tol=1e-9)
        window_cost = distance / math.hypot(*limits)
    assert math.isclose(metrics["window"], window_cost, abs_tol=1e-9)

    def gap(i, j):
        a, b = items[i]["box_m"], items[j]["box_m"]
        return math.hypot(max(a[0]-b[2], b[0]-a[2], 0), max(a[1]-b[3], b[1]-a[3], 0))

    def wall_gap(i):
        x1, y1, x2, y2 = items[i]["box_m"]
        return min(1, min(x1, y1, limits[0]-x2, limits[1]-y2)/.50)

    weight = rules["weight_within_room"]
    kind = room.get("kind", "bedroom")
    wall = statistics.mean(wall_gap(i) for i in spec.get("wall_indices", [0, 1, 5]))
    if kind == "bedroom":
        other_cost = .30*wall + .20*min(1, abs(gap(0, 4)-.05)/1.5) + .25*abs(gap(2, 3)-.10)/1.5
    else:
        if room.get("functional") and kind == "kitchen":
            base = (.35*wall + .40*(metrics["join_a_m"]+metrics["join_b_m"])/.10
                    + .25*max(.80-gap(3, 2), 0)/.80)
        elif room.get("functional") and kind == "living":
            base = (.25*wall + .35*min(1, abs(metrics["sofa_tv_gap_m"]-1.70)/1.50)
                    + .20*abs(metrics["sofa_table_gap_m"]-.45)/.10
                    + .20*min(1, abs(gap(3, 1)-.45)/1.50))
        else:
            base = .30 * wall
            for relation, relation_weight in zip(spec["relations"], [.25, .20, .25], strict=True):
                error = relation["target_m"] - gap(relation["first"], relation["second"])
                error = max(0, error) if relation["mode"] == "minimum" else abs(error)
                base += relation_weight * min(1, error/1.5)
        other_cost = (1-weight) * min(1, base)
    room_soft = other_cost + weight*window_cost
    assert math.isclose(metrics["room_soft"], room_soft, abs_tol=1e-9)
    assert math.isclose(metrics["soft"], .50*room_soft + .30*metrics["crowd"] +
                        .20*metrics["empty"], abs_tol=1e-9)


def verify_balance(room, boxes, zones, solution):
    m = solution["metrics"]
    gaps = [math.hypot(max(a[0]-b[2], b[0]-a[2], 0),
                       max(a[1]-b[3], b[1]-a[3], 0))
            for i, a in enumerate(boxes) for j, b in enumerate(boxes)
            if j > i and not (room.get("functional") and room.get("kind") == "kitchen" and j < 3)]
    crowd = statistics.mean(max(1-gap/.25, 0) for gap in gaps)
    assert abs(crowd-m["crowd"]) < 1e-9
    occupied = boxes + zones
    if room.get("functional"):
        occupied += [solution["functional_zone"]]
    width, height = room["width"], room["height"]
    radius = 0
    for i in range(9):
        x = width*(i+.5)/9
        for j in range(9):
            y = height*(j+.5)/9
            clearance = min(x, y, width-x, height-y,
                            *(math.hypot(max(a[0]-x, x-a[2], 0), max(a[1]-y, y-a[3], 0))
                              for a in occupied))
            radius = max(radius, clearance)
    empty = max(0, (radius/min(width, height)-.18)/.32)
    assert abs(radius-m["empty_radius_m"]) < 1e-9
    assert abs(empty-m["empty"]) < 1e-9


def verify_functional(room, solution):
    items = solution["furniture"]
    m = solution["metrics"]
    face = tuple(items[0]["front_xy"])
    assert face in {(0, 1), (0, -1), (-1, 0), (1, 0)}
    axis = 0 if face[0] else 1
    sign = face[axis]
    other = 1-axis
    boxes = [f["box_m"] for f in items]
    normal_limit = room["width"] if axis == 0 else room["height"]
    bounds = [(b[axis], b[axis+2]) if sign > 0 else
              (normal_limit-b[axis+2], normal_limit-b[axis]) for b in boxes]
    lateral = [(b[other], b[other+2]) for b in boxes]
    zone = solution["functional_zone"]
    z_normal = (zone[axis], zone[axis+2]) if sign > 0 else (
        normal_limit-zone[axis+2], normal_limit-zone[axis])
    z_lateral = (zone[other], zone[other+2])
    near = lambda a, b: math.isclose(a, b, abs_tol=1e-8)
    blocked = lambda rect: sum(area_intersection(b, rect) for b in boxes)
    obs = blocked(zone)
    assert near(m["clearance_m2"], obs)
    if room["kind"] == "kitchen":
        assert all(tuple(i["front_xy"]) == face for i in items[:3])
        assert all(all(near(a, b) for a, b in zip(pair, bounds[0])) for pair in bounds[:3])
        assert -1e-9 <= bounds[0][0] <= .030000001
        order = sorted(range(3), key=lambda i: lateral[i][0])
        assert order in ([0, 1, 2], [2, 1, 0])
        gaps = [lateral[j][0]-lateral[i][1] for i, j in zip(order, order[1:])]
        if order[0] == 2:
            gaps.reverse()
        assert all(.009999999 <= g <= .050000001 for g in gaps)
        assert near(gaps[0], m["join_a_m"]) and near(gaps[1], m["join_b_m"])
        assert near(z_normal[0], bounds[0][1]) and near(z_normal[1]-z_normal[0], .85)
        assert near(z_lateral[0], lateral[order[0]][0]) and near(z_lateral[1], lateral[order[-1]][1])
    else:
        assert tuple(items[2]["front_xy"]) == tuple(-v for v in face)
        assert all(near(sum(pair), sum(lateral[0])) for pair in lateral[:3])
        gap1 = bounds[1][0]-bounds[0][1]
        gap2 = bounds[2][0]-bounds[1][1]
        assert .349999999 <= gap1 <= .550000001 and gap2-gap1 >= .149999999
        assert near(gap1, m["sofa_table_gap_m"]) and near(gap2, m["table_tv_gap_m"])
        assert near(z_normal[0], bounds[0][1]) and near(z_normal[1], bounds[2][0])
        assert near(z_lateral[1]-z_lateral[0], .55)
        assert near(z_lateral[1], lateral[1][0]) or near(z_lateral[0], lateral[1][1])
        other_zone = list(zone)
        shift = (lateral[1][1]-lateral[1][0])+.55
        if near(z_lateral[0], lateral[1][1]):
            shift = -shift
        other_zone[other] += shift
        other_zone[other+2] += shift
        assert obs <= blocked(other_zone)+1e-8
    return obs


def verify_desk_chair(spec, solution):
    rule = spec["desk_chair"]
    desk = solution["furniture"][rule["desk_index"]]
    chair = solution["furniture"][rule["chair_index"]]
    desk_front = tuple(desk["front_xy"])
    assert desk_front in {(0, 1), (0, -1), (-1, 0), (1, 0)}
    assert tuple(chair["front_xy"]) == tuple(-component for component in desk_front)
    axis = 0 if desk_front[0] else 1
    lateral = 1 - axis
    db, cb = desk["box_m"], chair["box_m"]
    assert math.isclose(db[lateral] + db[lateral + 2], cb[lateral] + cb[lateral + 2], abs_tol=1e-9)
    gap = cb[axis] - db[axis + 2] if desk_front[axis] > 0 else db[axis] - cb[axis + 2]
    minimum, maximum = rule["gap_range_m"]
    assert minimum - 1e-9 <= gap <= maximum + 1e-9
    assert math.isclose(solution["metrics"]["desk_chair"], abs(gap - .10) / 1.5, abs_tol=1e-9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    args = parser.parse_args()
    root = Path(args.results)
    meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    with (root / "runs.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with (root / "summary.csv").open(encoding="utf-8-sig", newline="") as handle:
        summary = list(csv.DictReader(handle))
    expected = len(meta["rooms"]) * len(meta["methods"]) * len(meta["seeds"])
    assert len(rows) == expected
    assert len({(r["room"], r["method"], r["seed"]) for r in rows}) == expected
    initial_by_case = {}
    for row in rows:
        key, method, seed = row["room"], row["method"], int(row["seed"])
        result = json.loads((root / "solutions" / f"{key}_{method}_seed{seed:02d}.json").read_text(encoding="utf-8"))
        room = meta["rooms"][key]
        spec = meta.get("room_specs", {}).get(key, {})
        boxes = [f["box_m"] for f in result["best"]["furniture"]]
        expected_furniture = spec.get("furniture", meta["furniture"])
        assert len(boxes) == len(expected_furniture)
        for box, item, fixed in zip(boxes, result["best"]["furniture"], expected_furniture):
            x1, y1, x2, y2 = box
            assert all(item[field] == fixed[field] for field in ("name", "width", "depth"))
            assert item["rotation_deg"] in (0, 90)
            assert -1e-9 <= x1 < x2 <= room["width"]+1e-9
            assert -1e-9 <= y1 < y2 <= room["height"]+1e-9
            size = [item["width"], item["depth"]]
            if item["rotation_deg"] == 90:
                size.reverse()
            assert abs(x2-x1-size[0]) < 1e-9 and abs(y2-y1-size[1]) < 1e-9
        overlap = sum(area_intersection(a, b) for i, a in enumerate(boxes) for b in boxes[i+1:])
        zones = spec.get("zones", [[.25, 0., 1.15, 1.], [.25, 1., 1.15, 2.2]])
        door, passage = [sum(area_intersection(box, zone) for box in boxes) for zone in zones]
        total = overlap + door + passage
        metrics = result["best"]["metrics"]
        if isinstance(spec.get("window"), dict):
            verify_window(room, spec, result["initial"])
            verify_window(room, spec, result["best"])
            window = result["best"]["window"]
            assert row["window_wall"] == window["wall"]
            assert window["center_m"] == [float(row["window_center_x_m"]), float(row["window_center_y_m"])]
            assert float(row["window"]) == metrics["window"]
            if "window_distance_m" in metrics:
                assert float(row["window_distance_m"]) == metrics["window_distance_m"]
            else:
                assert row["window_on_sofa_side"] == str(metrics["window_on_sofa_side"])
        if room.get("functional"):
            verify_functional(room, result["initial"])
            total += verify_functional(room, result["best"])
        if "desk_chair" in spec:
            verify_desk_chair(spec, result["initial"])
            verify_desk_chair(spec, result["best"])
        if "crowd" in metrics:
            verify_balance(room, boxes, zones, result["best"])
            for field in ("crowd", "empty", "empty_radius_m"):
                assert abs(float(row[field])-metrics[field]) < 1e-9
        for name, expected_value in [("overlap_m2", overlap), ("door_m2", door),
                                     ("passage_m2", passage), ("violation_m2", total)]:
            assert abs(metrics[name]-expected_value) < 1e-9
            assert abs(float(row[name])-expected_value) < 1e-9
        assert metrics["feasible"] == (total <= 1e-9)
        assert (row["feasible"] == "True") == metrics["feasible"]
        assert abs(float(row["cost"])-metrics["cost"]) < 1e-12
        history = result["history"]
        assert len(history) == meta["config"]["generations"]+1
        initial = result["initial"]
        assert initial == initial_by_case.setdefault((key, seed), initial)
        assert history[0]["cost"] == initial["metrics"]["cost"]
        assert all(b["cost"] <= a["cost"]+1e-12 for a,b in zip(history, history[1:]))
        assert history[-1]["evaluations"] == meta["evaluations_per_run"]
        assert abs(history[-1]["cost"]-metrics["cost"]) < 1e-12
        expected_cost = metrics["soft"] if metrics["feasible"] else (
            2 + 10 * total / sum(f["width"] * f["depth"] for f in expected_furniture) + metrics["soft"])
        assert abs(expected_cost - metrics["cost"]) < 1e-8
    for row in summary:
        group = [r for r in rows if r["room"]==row["room"] and r["method"]==row["method"]]
        costs = [float(r["cost"]) for r in group]
        assert abs(statistics.mean(costs)-float(row["cost_mean"])) < 1e-12
        if len(group)>1:
            assert abs(statistics.stdev(costs)-float(row["cost_sd"])) < 1e-12
        assert sum(r["feasible"]=="True" for r in group) == int(row["feasible_runs"])
    audit = dict(status="PASS", audited_runs=len(rows),
                 checks=["导出矩形尺寸和边界", "独立计算重叠与禁放区面积", "可行性与分段代价", "共享初始最优布局", "JSON/CSV 一致性",
                         "每次运行的评估预算", "历史最优单调性", "汇总均值、标准差和成功次数"])
    if any(room.get("functional") for room in meta["rooms"].values()):
        audit["checks"].append("独立核对正面、同排或正对、间距及操作区占用")
    if any("desk_chair" in spec for spec in meta.get("room_specs", {}).values()):
        audit["checks"].append("独立核对卧室书桌与椅子的对中、相向与间距")
    if rows and "crowd" in rows[0]:
        audit["checks"].append("独立复算家具拥挤和留白指标")
    if rows and "window_wall" in rows[0]:
        audit["checks"].append("独立复算窗段墙面、端距、中心距离或沙发侧墙，以及加权软代价")
    (root / "verification.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
