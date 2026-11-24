"""从已保存的布局坐标绘制同种子三联图。"""
import argparse
import json
from pathlib import Path
import sys

from plot_results import plt, np, Rectangle, FURN_COLORS, draw_window, window_note
from matplotlib.patches import Polygon
from matplotlib.transforms import Bbox


def contains(outer, inner):
    return outer.contains(inner.x0, inner.y0) and outer.contains(inner.x1, inner.y1)


def label_regions(ax, regions, renderer, arrow_bounds):
    """把标签放在自身矩形内，避开其他矩形边缘及已放置的文字。"""
    boxes = [ax.transData.transform_bbox(Bbox.from_extents(*coords))
             for coords, _, _ in regions]
    placed = [ax.transData.transform_bbox(Bbox.from_extents(*bounds))
              for bounds in arrow_bounds]
    pad = renderer.points_to_pixels(1.5)
    shifts = (0, -.08, .08, -.15, .15, -.22, .22, -.30, .30, -.37, .37, -.44, .44)
    offsets = sorted(((x, y) for x in shifts for y in shifts),
                     key=lambda pair: pair[0]**2 + pair[1]**2)
    for i in sorted(range(len(boxes)), key=lambda k: boxes[k].width * boxes[k].height):
        own = boxes[i]
        _, name, color = regions[i]
        text = ax.text(0, 0, name, color=color, ha="center", va="center",
                       rotation_mode="anchor", zorder=5)
        others = boxes[:i] + boxes[i+1:]

        def find_position(allow_contained, allow_crossing=False):
            for size in (9, 8, 7, 6, 5):
                text.set_fontsize(size)
                for dx, dy in offsets:
                    x = own.x0 + (.5 + dx)*own.width
                    y = own.y0 + (.5 + dy)*own.height
                    text.set_position(ax.transData.inverted().transform((x, y)))
                    for rotation in (0, 90):
                        text.set(rotation=rotation, rotation_mode="anchor")
                        extent = text.get_window_extent(renderer).padded(pad)
                        if not contains(own, extent):
                            continue
                        if any(b.overlaps(extent) for b in placed):
                            continue
                        if not allow_crossing and any(b.overlaps(extent) and
                                                      not (allow_contained and contains(b, extent))
                                                      for b in others):
                            continue
                        return extent
            return None

        # 初始布局本身可能有重叠，允许落在重叠内部，但不能压过边界。
        extent = find_position(False)
        if extent is None:
            extent = find_position(True)
        if extent is None:
            # 对存在真实家具重叠的候选，优先保证名称仍在自身色块内且不压住其他文字。
            extent = find_position(True, allow_crossing=True)
        if extent is None:
            raise ValueError(f"无法放置图内标签：{ax.get_title()} / {name}")
        placed.append(extent)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="figures")
    parser.add_argument("--rooms", nargs="+", help="不指定时绘制全部场景")
    parser.add_argument("--seed", type=int, default=20)
    parser.add_argument("--qa-tools", type=Path, help="可选：绘图对齐审计脚本目录")
    args = parser.parse_args(argv)
    root, out = Path(args.results), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    audit = None
    if args.qa_tools:
        sys.path.insert(0, str(args.qa_tools.resolve()))
        from audit_panel_alignment import require_matplotlib_panel_alignment
        audit = require_matplotlib_panel_alignment
        (out / "qa").mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "sans-serif",
                         "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
                         "font.size": 9, "svg.fonttype": "none", "pdf.fonttype": 42,
                         "legend.frameon": False})
    meta = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    rooms = args.rooms or list(meta["rooms"])
    for key in rooms:
        room = meta["rooms"][key]
        spec = meta["room_specs"][key]
        w, h = room["width"], room["height"]
        ga, rs = [(json.loads((root / "solutions" / f"{key}_{m}_seed{args.seed:02d}.json")
                              .read_text(encoding="utf-8"))) for m in ("ga", "random")]
        assert ga["initial"] == rs["initial"]
        fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
        fig.subplots_adjust(left=.060, right=.980, bottom=.16, top=.775, wspace=.24)
        fig.suptitle(f"{room['title']}  {w:.2f} × {h:.2f} m  |  {w*h:.2f} m²  |  种子 {args.seed}", y=.962)
        examples = (ga["initial"], rs["best"], ga["best"])
        titles = ("共享初始最优布局", "随机搜索 RS", "遗传算法 GA")
        label_sets = []
        for ax, label, title, example in zip(axes, "abc", titles, examples):
            regions = []
            arrow_bounds = []
            for item, color, definition in zip(example["furniture"], FURN_COLORS, spec["furniture"]):
                x1, y1, x2, y2 = item["box_m"]
                ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fc=color,
                                       ec="#46525C", lw=.85, alpha=.88, zorder=2))
                name = definition["name"]
                if room.get("functional") and name == "操作台":
                    name = "备餐台面"
                regions.append((item["box_m"], name, "#152331"))
                if "front_xy" in item:
                    front = np.array(item["front_xy"])
                    side = np.array([-front[1], front[0]])
                    center = np.array([(x1+x2)/2, (y1+y2)/2])
                    half_depth = np.dot(np.abs(front), [(x2-x1)/2, (y2-y1)/2])
                    tip = center + (half_depth-.035)*front
                    base = tip - .11*front
                    vertices = np.array([tip, base+.07*side, base-.07*side])
                    ax.add_patch(Polygon(vertices, fc="#243A4A", ec="none", zorder=4))
                    arrow_bounds.append((*vertices.min(axis=0), *vertices.max(axis=0)))
            for zone, name in zip(spec["zones"], ("门前区", "通道")):
                x1, y1, x2, y2 = zone
                ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fc="#923D5230",
                                       edgecolor="#923D52", lw=.7, zorder=3))
                regions.append((zone, name, "#80243C"))
            label_sets.append((regions, arrow_bounds))
            ax.add_patch(Rectangle((0, 0), w, h, fc="none", ec="#28353F", lw=1.2))
            dx1, _, dx2, _ = spec["zones"][0]
            ax.plot([dx1, dx2], [0, 0], lw=2.6, color="#923D52", solid_capstyle="butt")
            ax.annotate("门", ((dx1+dx2)/2, 0), xytext=(0, -9), textcoords="offset points",
                        ha="center", va="top", color="#80243C")
            draw_window(ax, example, spec.get("window"))
            m = example["metrics"]
            note = (f"\n窗位  {window_note(example)}" if "window" in example else
                    f"\n拥挤罚分 {m['crowd']:.3f}  |  最大估计空块半径 {m['empty_radius_m']:.2f} m")
            ax.set_title(f"({label}) {title}\n代价 = {m['cost']:.4g}  |  违规面积 = {m['violation_m2']:.4g} m²{note}", pad=8)
            ax.set(xlim=(-.08, w+.08), ylim=(-.38, h+.18), xticks=np.arange(int(w)+1),
                   yticks=np.arange(int(h)+1), xlabel="x / m")
            ax.set_aspect("equal")
            ax.patch.set_visible(False)
            for spine in ax.spines.values():
                spine.set_visible(False)
        axes[0].set_ylabel("y / m")
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for ax, (regions, arrow_bounds) in zip(axes, label_sets):
            label_regions(ax, regions, renderer, arrow_bounds)
        stem = f"layout_{key}"
        if audit:
            audit(fig, json_out=out / "qa" / f"{stem}.alignment.json", strict=True)
        fig.savefig(out / f"{stem}.png", dpi=600)
        fig.savefig(out / f"{stem}.svg")
        fig.savefig(out / f"{stem}.pdf")
        plt.close(fig)


if __name__ == "__main__":
    main()
