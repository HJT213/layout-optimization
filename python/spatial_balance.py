"""面向八个场景的家具间距与局部留白评分。"""
from functools import lru_cache
import numpy as np

GRID = 9
PREFERRED_GAP = .25
EMPTY_RADIUS_FRACTION = .18
CROWD_WEIGHT = .30
EMPTY_WEIGHT = .20


@lru_cache(maxsize=None)
def probes(width, height):
    fractions = (np.arange(GRID)+.5)/GRID
    x, y = np.meshgrid(width*fractions, height*fractions)
    points = np.column_stack((x.ravel(), y.ravel()))
    boundary = np.minimum(points, np.array([width, height])-points).min(axis=1)
    return points, boundary


def spatial_terms(boxes, room, entrance_zones, functional_zone):
    ii, jj = np.triu_indices(boxes.shape[1], 1)
    if room.functional and room.kind == "kitchen":
        keep = jj >= 3  # 台面模块设计为相接，接缝不计入拥挤。
        ii, jj = ii[keep], jj[keep]
    a, b = boxes[:, ii], boxes[:, jj]
    delta = np.maximum(np.maximum(a[..., :2]-b[..., 2:], b[..., :2]-a[..., 2:]), 0)
    distances = np.hypot(delta[..., 0], delta[..., 1])
    crowd = np.maximum(1-distances/PREFERRED_GAP, 0).mean(axis=1)

    points, boundary = probes(room.width, room.height)
    radius = np.broadcast_to(boundary, (len(boxes), len(points))).copy()

    def consider(rectangles):
        for rect in rectangles.transpose(1, 0, 2):
            dx = np.maximum(np.maximum(rect[:, None, 0]-points[:, 0],
                                       points[:, 0]-rect[:, None, 2]), 0)
            dy = np.maximum(np.maximum(rect[:, None, 1]-points[:, 1],
                                       points[:, 1]-rect[:, None, 3]), 0)
            np.minimum(radius, np.hypot(dx, dy), out=radius)

    consider(boxes)
    consider(np.broadcast_to(entrance_zones, (len(boxes), *entrance_zones.shape)))
    if functional_zone is not None:
        consider(functional_zone[:, None, :])
    max_radius = radius.max(axis=1)
    scale = min(room.width, room.height)
    empty = np.clip((max_radius/scale-EMPTY_RADIUS_FRACTION)/(.5-EMPTY_RADIUS_FRACTION), 0, 1)
    return dict(crowd=crowd, empty=empty, empty_radius_m=max_radius)


def combine(base, terms):
    return ((1-CROWD_WEIGHT-EMPTY_WEIGHT)*base +
            CROWD_WEIGHT*terms["crowd"] + EMPTY_WEIGHT*terms["empty"])
