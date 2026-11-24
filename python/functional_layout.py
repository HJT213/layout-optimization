"""观影型客厅与一字型厨房的组合编码（距离为仿真设定）。"""
import numpy as np

FRONTS = ((0, 1), (-1, 0), (0, -1), (1, 0))
KITCHEN_CLEARANCE = .85
KITCHEN_GAPS = (.01, .05)
SOFA_GAP = (.35, .55)
TV_EXTRA_GAP = .15
LIVING_BYPASS = .55


def transform(u0, v0, u1, v1, turn, room):
    """将沿墙/朝室内的局部矩形映射为世界坐标轴对齐矩形。"""
    candidates = np.stack((
        np.stack((u0, v0, u1, v1), axis=-1),
        np.stack((room.width-v1, u0, room.width-v0, u1), axis=-1),
        np.stack((room.width-u1, room.height-v1, room.width-u0, room.height-v0), axis=-1),
        np.stack((v0, room.height-u1, v1, room.height-u0), axis=-1),
    ), axis=1)
    return candidates[np.arange(len(turn)), turn]


def arrange(genes, boxes, room):
    """前三件由共享的组合参数定位，其余物体仍独立搜索。"""
    g = np.clip(genes[:, :3, :2], 0, 1)
    widths = [f.width for f in room.furniture[:3]]
    depths = [f.depth for f in room.furniture[:3]]
    along = np.array([room.width, room.height]*2)
    normal = np.array([room.height, room.width]*2)
    options = np.arange(4)
    if room.kind == "kitchen":
        required = sum(widths) + 2*KITCHEN_GAPS[1]
        options = options[(along >= required) & (normal >= max(depths)+KITCHEN_CLEARANCE+.03)]
        if not len(options):
            raise ValueError("没有可容纳三段台面的墙面")
    else:
        required = sum(depths)+2*SOFA_GAP[0]+TV_EXTRA_GAP
        options = options[(along >= max(widths)) & (normal >= required+.08)]
        if not len(options):
            raise ValueError("没有可容纳观影组合的墙面")
    turn = options[np.minimum((g[:, 0, 0]*len(options)).astype(int), len(options)-1)]
    span, depth = along[turn], normal[turn]
    directions = np.broadcast_to(np.asarray(FRONTS)[turn, None, :], (len(g), 3, 2)).copy()
    if room.kind == "kitchen":
        gap1 = KITCHEN_GAPS[0]+np.diff(KITCHEN_GAPS)[0]*g[:, 1, 0]
        gap2 = KITCHEN_GAPS[0]+np.diff(KITCHEN_GAPS)[0]*g[:, 1, 1]
        total = sum(widths)+gap1+gap2
        start = g[:, 0, 1]*(span-total)
        end = start+total
        reverse = g[:, 2, 0] >= .5
        starts = (np.where(reverse, end-widths[0], start),
                  np.where(reverse, start+widths[2]+gap2, start+widths[0]+gap1),
                  np.where(reverse, start, end-widths[2]))
        back = g[:, 2, 1]*.03
        for i, u in enumerate(starts):
            boxes[:, i] = transform(u, back, u+widths[i], back+depths[i], turn, room)
        front = back+depths[0]
        use_zones = transform(start, front, end, front+KITCHEN_CLEARANCE, turn, room)[:, None]
        detail = dict(join_a_m=gap1, join_b_m=gap2, counter_wall_gap_m=back)
    else:
        sofa_depth, table_depth, tv_depth = depths
        half_width = max(widths)/2
        lateral = half_width+g[:, 0, 1]*(span-2*half_width)
        tv_back = depth-g[:, 2, 1]*.08
        tv_face = tv_back-tv_depth
        max_gap1 = np.minimum(SOFA_GAP[1], (tv_face-sofa_depth-table_depth-TV_EXTRA_GAP)/2)
        gap1 = np.minimum(SOFA_GAP[0]+np.diff(SOFA_GAP)[0]*g[:, 1, 0], max_gap1)
        min_gap2 = gap1+TV_EXTRA_GAP
        max_gap2 = tv_face-sofa_depth-gap1-table_depth
        gap2 = min_gap2+g[:, 1, 1]*(max_gap2-min_gap2)
        table_front = tv_face-gap2
        table_back = table_front-table_depth
        sofa_face = table_back-gap1
        for i, (v0, v1) in enumerate(((sofa_face-sofa_depth, sofa_face),
                                       (table_back, table_front), (tv_face, tv_back))):
            u = lateral-widths[i]/2
            boxes[:, i] = transform(u, v0, u+widths[i], v1, turn, room)
        directions[:, 2] *= -1
        left, right = lateral-widths[1]/2, lateral+widths[1]/2
        use_zones = np.stack((
            transform(left-LIVING_BYPASS, sofa_face, left, tv_face, turn, room),
            transform(right, sofa_face, right+LIVING_BYPASS, tv_face, turn, room),
        ), axis=1)
        detail = dict(sofa_table_gap_m=gap1, table_tv_gap_m=gap2,
                      sofa_tv_gap_m=tv_face-sofa_face)
    return boxes, directions, use_zones, detail
