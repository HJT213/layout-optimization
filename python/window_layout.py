"""单扇窗的墙面编码和房型偏好。尺寸与边距单位为米。"""
from math import hypot
import numpy as np

WIDTHS = {"bedroom": 1.40, "bathroom": .80, "kitchen": 1.00, "living": 1.60}
TARGETS = {"bedroom": (2, "书桌"), "bathroom": (0, "淋浴区"), "kitchen": (2, "灶台")}
WALLS = ("opposite", "right")
MARGIN = .20
WEIGHT = .25


def window_spec(room):
    return dict(width_m=WIDTHS[room.kind], corner_margin_m=MARGIN, walls=list(WALLS),
                weight_within_room=WEIGHT, target=TARGETS.get(room.kind, (0, "沙发"))[1],
                rule="sofa_side_wall" if room.kind == "living" else "center_distance")


def decode_window(genes, room):
    genes = np.asarray(genes)
    if genes.ndim == 2:
        genes = genes[None]
    if genes.shape[1] == len(room.furniture):
        # 兼容只含家具基因的旧调用，默认将窗置于对面墙中央。
        position = np.full(len(genes), .5)
        right = np.zeros(len(genes), dtype=bool)
    else:
        position = np.clip(genes[:, -1, 0], 0, 1)
        right = genes[:, -1, 2] >= .5
    width = WIDTHS[room.kind]
    if min(room.width, room.height) < width + 2 * MARGIN:
        raise ValueError("窗宽与端部边距超过可选墙长")
    length = np.where(right, room.height, room.width)
    start = MARGIN + position * (length - width - 2 * MARGIN)
    end = start + width
    a = np.column_stack((np.where(right, room.width, start),
                         np.where(right, start, room.height)))
    b = np.column_stack((np.where(right, room.width, end),
                         np.where(right, end, room.height)))
    return right, a, b


def window_metrics(genes, room, boxes, fronts=None):
    right, a, b = decode_window(genes, room)
    if room.kind == "living":
        if fronts is None:
            # 通用矩形解码只记录旋转，轴向足以判定侧墙。
            sofa = np.asarray(genes)[..., 0, 2] >= .5
            faces_y = ~np.atleast_1d(sofa)
        else:
            faces_y = fronts[:, 0, 1] != 0
        side = right == faces_y
        return dict(window=(~side).astype(float), window_on_sofa_side=side)
    target, _ = TARGETS[room.kind]
    box = boxes[:, target]
    delta = (a + b - box[:, :2] - box[:, 2:]) / 2
    distance = np.hypot(delta[:, 0], delta[:, 1])
    return dict(window=distance / hypot(room.width, room.height), window_distance_m=distance)


def add_window_score(base, metrics):
    return (1 - WEIGHT) * base + WEIGHT * metrics["window"]
