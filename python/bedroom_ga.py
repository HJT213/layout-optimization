"""二维家具布局：场景配置、混合编码、遗传算法及随机搜索。"""
from dataclasses import dataclass, asdict, replace
from math import sqrt
from time import perf_counter
import numpy as np
from spatial_balance import spatial_terms, combine
from window_layout import WALLS, WEIGHT, add_window_score, decode_window, window_metrics, window_spec


@dataclass(frozen=True)
class Furniture:
    name: str
    width: float
    depth: float


FURNITURE = (
    Furniture("床", 1.5, 2.0),
    Furniture("衣柜", 1.8, 0.6),
    Furniture("书桌", 1.2, 0.6),
    Furniture("椅子", 0.5, 0.5),
    Furniture("床头柜", 0.5, 0.5),
    Furniture("书架", 0.9, 0.35),
)
DESK_INDEX, CHAIR_INDEX = 2, 3
DESK_CHAIR_GAP = (.10, .35)


@dataclass(frozen=True)
class Room:
    key: str
    title: str
    width: float
    height: float
    kind: str = "bedroom"
    functional: bool = False
    smaller_fixtures: bool = False

    @property
    def furniture(self):
        if self.smaller_fixtures:
            return SMALL_FIXTURES[self.kind]
        return FURNITURE if self.kind == "bedroom" else RULES[self.kind].furniture

    @property
    def zones(self):
        # 两个区域互不重叠，避免同一占用面积被重复计罚。
        if self.kind == "bedroom":
            return np.array([[0.25, 0.0, 1.15, 1.0],
                             [0.25, 1.0, 1.15, 2.2]])
        x1, x2, front, end = RULES[self.kind].entry
        return np.array([[x1, 0.0, x2, front], [x1, front, x2, end]])

@dataclass(frozen=True)
class Relation:
    name: str
    first: int
    second: int
    target_m: float
    mode: str = "target"


@dataclass(frozen=True)
class RoomRules:
    furniture: tuple[Furniture, ...]
    entry: tuple[float, float, float, float]
    wall_indices: tuple[int, ...]
    relations: tuple[Relation, Relation, Relation]


RULES = {
    "bathroom": RoomRules(
        (Furniture("淋浴区", .90, .90), Furniture("马桶", .40, .70),
         Furniture("洗手台", .75, .48), Furniture("洗衣机", .60, .62),
         Furniture("收纳柜", .45, .35)),
        (.15, .90, .75, 1.45), (0, 1, 2, 3, 4),
        (Relation("淋浴区与马桶保持距离", 0, 1, .45, "minimum"),
         Relation("马桶与洗手台邻近", 1, 2, .30),
         Relation("洗衣机与收纳柜邻近", 3, 4, .10)),
    ),
    "kitchen": RoomRules(
        (Furniture("水槽", .80, .60), Furniture("操作台", 1.20, .60),
         Furniture("灶台", .65, .60), Furniture("冰箱", .70, .70),
         Furniture("储物柜", .90, .50), Furniture("备餐车", .60, .40)),
        (.25, 1.15, .90, 1.75), (0, 1, 2, 3, 4),
        (Relation("水槽靠近操作台", 0, 1, .05),
         Relation("操作台靠近灶台", 1, 2, .10),
         Relation("冰箱远离灶台", 3, 2, .80, "minimum")),
    ),
    "living": RoomRules(
        (Furniture("沙发", 2.20, .85), Furniture("茶几", 1.00, .55),
         Furniture("电视柜", 1.60, .42), Furniture("单人椅", .75, .75),
         Furniture("边柜", .90, .42), Furniture("书架", .88, .32)),
        (.30, 1.25, 1.00, 2.10), (0, 2, 4, 5),
        (Relation("沙发与电视柜的间距", 0, 2, 1.70),
         Relation("沙发与茶几的间距", 0, 1, .45),
         Relation("单人椅与茶几的间距", 3, 1, .45)),
    ),
}


SMALL_FIXTURES = {
    "bathroom": (Furniture("淋浴区", .80, .80), Furniture("马桶", .38, .62),
                 Furniture("洗手台", .50, .38), Furniture("洗衣机", .50, .50),
                 Furniture("收纳柜", .30, .28)),
    "kitchen": (Furniture("水槽", .65, .50), Furniture("操作台", 1.00, .50),
                Furniture("灶台", .60, .50), Furniture("冰箱", .65, .65),
                Furniture("储物柜", .55, .45), Furniture("备餐车", .35, .35)),
}

COMPACT_AREA_RATIO = 2 / 3
COMPACT_LINEAR_SCALE = sqrt(COMPACT_AREA_RATIO)

ROOMS = {
    "standard": Room("standard", "标准卧室", 5.0, 4.0),
    "bathroom_standard": Room("bathroom_standard", "标准卫生间", 3.0, 2.6, "bathroom"),
    "kitchen_standard": Room("kitchen_standard", "标准厨房", 4.0, 3.2, "kitchen"),
    "living_standard": Room("living_standard", "标准客厅", 5.6, 4.4, "living"),
}
for key, standard_room in tuple(ROOMS.items()):
    compact_key = key.replace("standard", "compact")
    ROOMS[compact_key] = replace(standard_room, key=compact_key,
                                 title=standard_room.title.replace("标准", "紧凑"),
                                 width=standard_room.width * COMPACT_LINEAR_SCALE,
                                 height=standard_room.height * COMPACT_LINEAR_SCALE)


def room_spec(room):
    base = dict(furniture=[asdict(item) for item in room.furniture],
                zones=room.zones.tolist(), window=window_spec(room))
    if room.kind == "bedroom":
        base["desk_chair"] = dict(desk_index=DESK_INDEX, chair_index=CHAIR_INDEX,
                                 gap_range_m=DESK_CHAIR_GAP)
    else:
        rules = RULES[room.kind]
        base.update(wall_indices=list(rules.wall_indices),
                    relations=[asdict(item) for item in rules.relations])
    return base


@dataclass(frozen=True)
class GAConfig:
    population: int = 80
    generations: int = 200
    elite: int = 4
    tournament: int = 3
    crossover: float = 0.9
    mutation: float = 0.2
    rotation_mutation: float = 0.05
    sigma_start: float = 0.12
    sigma_end: float = 0.025

    def validate(self):
        if self.population < 4 or not 0 < self.elite < self.population:
            raise ValueError("population >= 4，且 0 < elite < population")
        if self.generations < 1 or self.tournament < 2:
            raise ValueError("generations >= 1，tournament >= 2")
        for value in (self.crossover, self.mutation, self.rotation_mutation):
            if not 0 <= value <= 1:
                raise ValueError("概率必须位于 [0,1]")

    @property
    def evaluations(self):
        return self.population + self.generations * (self.population - self.elite)


def sample_population(rng, count, n_furniture=len(FURNITURE), *, include_window=False):
    blocks = n_furniture + int(include_window)
    genes = rng.random((count, blocks, 3))
    genes[:, :, 2] = rng.integers(0, 2, (count, blocks))
    return genes


def desk_front(genes):
    desk_rotated = genes[..., DESK_INDEX, 2] >= .5
    reverse = genes[..., CHAIR_INDEX, 2] >= .5
    front = np.stack((-desk_rotated.astype(int), (~desk_rotated).astype(int)), axis=-1)
    return np.where(reverse[..., None], -front, front)


def decode(genes, room, *, with_function=False):
    """每件家具 (u,v,r)，映射为 [xmin,ymin,xmax,ymax]；始终在房间内。"""
    genes = np.asarray(genes, dtype=float)
    single = genes.ndim == 2
    if single:
        genes = genes[None]
    wh = np.array([(f.width, f.depth) for f in room.furniture])
    if genes.ndim != 3 or genes.shape[1] not in (len(wh), len(wh) + 1) or genes.shape[2] != 3:
        raise ValueError("家具数量与染色体形状不匹配")
    genes = genes[:, :len(wh)]
    rotated = genes[:, :, 2] >= 0.5
    size = np.where(rotated[:, :, None], wh[None, :, ::-1], wh[None])
    available = np.array([room.width, room.height]) - size
    if np.any(available < 0):
        raise ValueError("家具尺寸超过房间尺寸")
    lower = np.clip(genes[:, :, :2], 0, 1) * available
    boxes = np.concatenate([lower, lower + size], axis=-1)
    if room.kind == "bedroom":
        # 书桌和椅子整体定位。椅子中心始终沿书桌正面的法线摆放。
        front = desk_front(genes)
        desk_size = size[:, DESK_INDEX]
        chair_size = np.where(rotated[:, DESK_INDEX, None],
                              wh[CHAIR_INDEX, ::-1], wh[CHAIR_INDEX])
        min_gap, max_gap = DESK_CHAIR_GAP
        gap = min_gap + np.clip(genes[:, CHAIR_INDEX, 0], 0, 1) * (max_gap - min_gap)
        normal_distance = ((np.abs(front) * (desk_size + chair_size)).sum(axis=1) / 2
                           + gap)
        offset = front * normal_distance[:, None]
        pair_low = np.minimum(-desk_size / 2, offset - chair_size / 2)
        pair_high = np.maximum(desk_size / 2, offset + chair_size / 2)
        room_size = np.array([room.width, room.height])
        pair_travel = room_size - (pair_high - pair_low)
        if np.any(pair_travel < 0):
            raise ValueError("房间无法容纳书桌与对中的椅子")
        desk_center = -pair_low + np.clip(genes[:, DESK_INDEX, :2], 0, 1) * pair_travel
        chair_center = desk_center + offset
        boxes[:, DESK_INDEX] = np.concatenate((desk_center - desk_size / 2,
                                               desk_center + desk_size / 2), axis=1)
        boxes[:, CHAIR_INDEX] = np.concatenate((chair_center - chair_size / 2,
                                                chair_center + chair_size / 2), axis=1)
    if room.functional:
        from functional_layout import arrange

        decoded = arrange(genes, boxes, room)
        if with_function:
            return decoded
        boxes = decoded[0]
    return boxes[0] if single else boxes


def intersection_area(a, b):
    sides = np.maximum(0.0, np.minimum(a[..., 2:], b[..., 2:])
                       - np.maximum(a[..., :2], b[..., :2]))
    return np.prod(sides, axis=-1)


def rectangle_gap(a, b):
    separation = np.maximum(0.0, np.maximum(a[..., :2] - b[..., 2:],
                                           b[..., :2] - a[..., 2:]))
    return np.linalg.norm(separation, axis=-1)


def evaluate(genes, room):
    """越小越好。可行解的 cost<=1，不可行解的 cost>2，保证可行性优先。"""
    if room.functional:
        boxes, fronts, use_zones, detail = decode(genes, room, with_function=True)
    else:
        boxes = decode(genes, room)
    if boxes.ndim == 2:
        boxes = boxes[None]
    ii, jj = np.triu_indices(len(room.furniture), 1)
    overlaps = intersection_area(boxes[:, ii], boxes[:, jj]).sum(axis=1)
    entrance_zones = room.zones
    blocked = intersection_area(boxes[:, :, None, :], entrance_zones[None, None]).sum(axis=1)
    violation = overlaps + blocked.sum(axis=1)
    feasible = violation <= 1e-9  # m² 数值容差，绝非 10cm 等物理宽限。
    wall_gaps = np.minimum.reduce([boxes[:, :, 0], boxes[:, :, 1],
                                  room.width - boxes[:, :, 2], room.height - boxes[:, :, 3]])
    if room.functional:
        occupied = intersection_area(boxes[:, :, None, :], use_zones[:, None]).sum(axis=1)
        clearance = occupied.min(axis=1)
        geometry_violation = violation.copy()
        violation += clearance
        feasible = violation <= 1e-9
        rules = RULES[room.kind]
        wall = np.minimum(wall_gaps[:, rules.wall_indices] / .50, 1).mean(axis=1)
        if room.kind == "kitchen":
            joins = (detail["join_a_m"] + detail["join_b_m"]) / .10
            fridge = rectangle_gap(boxes[:, 3], boxes[:, 2])
            fridge_gap = np.maximum(.80-fridge, 0) / .80
            soft = .35*wall + .40*joins + .25*fridge_gap
        else:
            viewing = np.minimum(np.abs(detail["sofa_tv_gap_m"]-1.70)/1.50, 1)
            coffee = np.abs(detail["sofa_table_gap_m"]-.45)/.10
            chair_gap = rectangle_gap(boxes[:, 3], boxes[:, 1])
            chair = np.minimum(np.abs(chair_gap-.45)/1.50, 1)
            soft = .25*wall + .35*viewing + .20*coffee + .20*chair
        primary_zone = use_zones[np.arange(len(boxes)), occupied.argmin(axis=1)]
        balance = spatial_terms(boxes, room, entrance_zones, primary_zone)
        window = window_metrics(genes, room, boxes, fronts)
        room_soft = add_window_score(np.clip(soft, 0, 1), window)
        soft = combine(room_soft, balance)
        total_area = sum(f.width * f.depth for f in room.furniture)
        cost = np.where(feasible, soft, 2 + 10*violation/total_area + soft)
        return dict(cost=cost, feasible=feasible, violation_m2=violation,
                    overlap_m2=overlaps, door_m2=blocked[:, 0], passage_m2=blocked[:, 1],
                    geometry_violation_m2=geometry_violation, clearance_m2=clearance,
                    soft=soft, room_soft=room_soft, wall=wall, **detail, **balance, **window)
    balance = spatial_terms(boxes, room, entrance_zones, None)
    window = window_metrics(genes, room, boxes)
    if room.kind != "bedroom":
        rules = RULES[room.kind]
        wall = np.minimum(wall_gaps[:, rules.wall_indices] / .50, 1).mean(axis=1)
        components = []
        for relation in rules.relations:
            gap = rectangle_gap(boxes[:, relation.first], boxes[:, relation.second])
            error = relation.target_m - gap
            error = np.maximum(error, 0) if relation.mode == "minimum" else np.abs(error)
            components.append(np.minimum(error / 1.50, 1))
        first, second, third = components
        room_soft = add_window_score(.30 * wall + .25 * first + .20 * second + .25 * third, window)
        soft = combine(room_soft, balance)
        total_area = sum(f.width * f.depth for f in room.furniture)
        cost = np.where(feasible, soft, 2.0 + 10.0 * violation / total_area + soft)
        return dict(cost=cost, feasible=feasible, violation_m2=violation,
                    overlap_m2=overlaps, door_m2=blocked[:, 0], passage_m2=blocked[:, 1],
                    soft=soft, room_soft=room_soft, wall=wall, relation_a=first,
                    relation_b=second, relation_c=third, **balance, **window)
    # 卧室保留原有软评分，书桌与椅子的对中和朝向由解码直接满足。
    wall = np.minimum(wall_gaps[:, [0, 1, 5]] / 0.5, 1.0).mean(axis=1)
    bedside = np.minimum(np.abs(rectangle_gap(boxes[:, 0], boxes[:, 4]) - 0.05) / 1.5, 1.0)
    desk_chair = np.minimum(np.abs(rectangle_gap(boxes[:, 2], boxes[:, 3]) - 0.10) / 1.5, 1.0)
    room_soft = 0.30 * wall + WEIGHT * window["window"] + 0.20 * bedside + 0.25 * desk_chair
    soft = combine(room_soft, balance)
    total_area = sum(f.width * f.depth for f in FURNITURE)
    cost = np.where(feasible, soft, 2.0 + 10.0 * violation / total_area + soft)
    return dict(cost=cost, feasible=feasible, violation_m2=violation,
                overlap_m2=overlaps, door_m2=blocked[:, 0], passage_m2=blocked[:, 1],
                soft=soft, room_soft=room_soft, wall=wall, bedside=bedside, desk_chair=desk_chair,
                **balance, **window)


def solution_details(genes, room):
    metrics = evaluate(genes, room)
    boxes = decode(genes, room)
    right, a, b = decode_window(genes, room)
    result = {
        "genes": np.asarray(genes).tolist(),
        "metrics": {key: value[0].item() for key, value in metrics.items()},
        "window": dict(wall=WALLS[int(right[0])], endpoints_m=[a[0].tolist(), b[0].tolist()],
                       center_m=((a[0] + b[0]) / 2).tolist()),
        "furniture": [dict(**asdict(f), rotation_deg=int(genes[i, 2] >= .5) * 90,
                           box_m=box.tolist())
                      for i, (f, box) in enumerate(zip(room.furniture, boxes))],
    }
    if room.functional:
        _, fronts, use_zones, _ = decode(genes, room, with_function=True)
        for i, front in enumerate(fronts[0]):
            item = result["furniture"][i]
            item["rotation_deg"] = 90 if front[0] else 0
            if room.kind == "kitchen" or i != 1:
                item["front_xy"] = front.tolist()
        occupied = intersection_area(boxes[:, None, :], use_zones[0][None]).sum(axis=0)
        result["functional_zone"] = use_zones[0, np.argmin(occupied)].tolist()
    elif room.kind == "bedroom":
        front = desk_front(np.asarray(genes))
        for i, direction in ((DESK_INDEX, front), (CHAIR_INDEX, -front)):
            item = result["furniture"][i]
            item["rotation_deg"] = 90 if direction[0] else 0
            item["front_xy"] = direction.tolist()
    return result


def optimize(room, config, seed, method="ga"):
    config.validate()
    if method not in {"ga", "random", "ga_no_mutation"}:
        raise ValueError("未知方法")
    started = perf_counter()
    # 三种方法使用完全相同的初始种群，后续使用独立随机流。
    n_furniture = len(room.furniture)
    blocks = n_furniture + 1
    initial = sample_population(np.random.default_rng(seed), config.population, n_furniture,
                                include_window=True)
    rng = np.random.default_rng(seed + (200000 if method == "random" else 100000))
    population = initial.copy()
    metrics = evaluate(population, room)
    costs = metrics["cost"]
    best_index = int(np.argmin(costs))
    best = population[best_index].copy()
    best_cost = float(costs[best_index])
    evaluations = config.population
    history = []

    best_metrics = {key: value[best_index] for key, value in metrics.items()}

    def record(generation):
        history.append(dict(generation=generation, evaluations=evaluations,
                            cost=float(best_metrics["cost"]),
                            feasible=bool(best_metrics["feasible"]),
                            violation_m2=float(best_metrics["violation_m2"]),
                            soft=float(best_metrics["soft"])))

    record(0)
    children_count = config.population - config.elite
    for generation in range(1, config.generations + 1):
        if method == "random":
            children = sample_population(rng, children_count, n_furniture, include_window=True)
        else:
            elites = population[np.argsort(costs, kind="stable")[:config.elite]].copy()
            def select():
                contestants = rng.integers(0, config.population,
                                          size=(children_count, config.tournament))
                winners = contestants[np.arange(children_count),
                                      np.argmin(costs[contestants], axis=1)]
                return population[winners]
            p1, p2 = select(), select()
            # 家具块均匀交叉；其中一部分坐标采用凸组合交叉，旋转保持离散。
            swap = rng.random((children_count, blocks, 1)) < 0.5
            children = np.where(swap, p1, p2).copy()
            alpha = rng.random((children_count, blocks, 1))
            blend = rng.random((children_count, blocks, 1)) < 0.35
            children[:, :, :2] = np.where(blend, alpha * p1[:, :, :2] + (1-alpha) * p2[:, :, :2],
                                         children[:, :, :2])
            perform = rng.random((children_count, 1, 1)) < config.crossover
            children = np.where(perform, children, p1)
            if method != "ga_no_mutation":
                progress = (generation - 1) / max(1, config.generations - 1)
                sigma = config.sigma_start + progress * (config.sigma_end - config.sigma_start)
                mask = rng.random((children_count, blocks, 2)) < config.mutation
                children[:, :, :2] += mask * rng.normal(0, sigma, mask.shape)
                flip = rng.random((children_count, blocks)) < config.rotation_mutation
                children[:, :, 2] = np.where(flip, 1 - children[:, :, 2], children[:, :, 2])
            children[:, :, :2] = np.clip(children[:, :, :2], 0, 1)
        child_metrics = evaluate(children, room)
        child_costs = child_metrics["cost"]
        evaluations += children_count
        index = int(np.argmin(child_costs))
        if child_costs[index] < best_cost:
            best_cost = float(child_costs[index])
            best = children[index].copy()
            best_metrics = {key: value[index] for key, value in child_metrics.items()}
        if method != "random":
            population = np.concatenate([elites, children])
            # 精英直接缓存代价，不额外评估，预算不包含日志的复算。
            costs = np.concatenate([np.sort(costs, kind="stable")[:config.elite], child_costs])
        record(generation)
    elapsed = perf_counter() - started
    assert evaluations == config.evaluations
    assert np.all(np.diff([row["cost"] for row in history]) <= 1e-12)
    return dict(method=method, seed=seed, seconds=elapsed, evaluations=evaluations,
                initial=solution_details(initial[best_index], room),
                best=solution_details(best, room), history=history)
