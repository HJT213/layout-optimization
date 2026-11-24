"""绘制每个房型的可行 GA 最低代价布局，并保存来源索引。"""
import argparse
import csv
import json
import math
from pathlib import Path
from plot_room_examples import FURN_COLORS, Polygon, Rectangle, label_regions, np, plt
from plot_results import draw_window, window_note


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--out", type=Path, default=Path("best_figures"))
    args = parser.parse_args()

    results = args.results
    meta = json.loads((results / "metadata.json").read_text(encoding="utf-8"))
    with (results / "runs.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    trials = len(meta["seeds"])
    index = []
    args.out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 10,
                         "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    for key, room in meta["rooms"].items():
        runs = [row for row in rows if row["room"] == key and row["method"] == "ga"]
        if len(runs) != trials or {int(row["seed"]) for row in runs} != set(meta["seeds"]):
            raise ValueError(f"Incomplete GA runs for {key}")
        if any(not math.isfinite(float(row["cost"])) for row in runs):
            raise ValueError(f"Invalid score for {key}")
        feasible = [row for row in runs if row["feasible"] == "True"]
        if not feasible:
            print(f"{room['title']} 没有可行的 GA 方案")
            continue
        winner = min(feasible, key=lambda row: (float(row["cost"]), int(row["seed"])))
        seed = int(winner["seed"])
        cost = float(winner["cost"])
        source = results / "solutions" / f"{key}_ga_seed{seed:02d}.json"
        saved = json.loads(source.read_text(encoding="utf-8"))
        solution = saved["best"]
        metrics = solution["metrics"]
        if (saved["method"], saved["seed"], metrics["cost"], metrics["feasible"]) != ("ga", seed, cost, True):
            raise ValueError(f"Run table and layout disagree for {key}")
        spec = meta["room_specs"][key]
        width, height = room["width"], room["height"]
        fig, ax = plt.subplots(figsize=(7.2, 6.4))
        fig.subplots_adjust(left=.13, right=.92, top=.76, bottom=.13)
        fig.text(.13, .946, f"{room['title']}  |  {width:.2f} × {height:.2f} m  ·  {width*height:.2f} m²",
                 fontsize=15, fontweight="bold", color="#152331")
        fig.text(.13, .898, f"遗传算法 GA  ·  {trials} 次中可行且代价最低  ·  种子 {seed}", color="#324656")
        fig.text(.13, .860, f"代价 {cost:.7g}  |  违规面积 {metrics['violation_m2']:.4g} m²",
                 color="#324656")
        fig.text(.13, .822, f"窗位  {window_note(solution)}", color="#057487")
        regions, arrows = [], []
        furniture = solution["furniture"]
        for item, color, definition in zip(furniture, FURN_COLORS[:len(furniture)], spec["furniture"], strict=True):
            if item["name"] != definition["name"]:
                raise ValueError(f"Unexpected furniture mapping in {source.name}")
            x1, y1, x2, y2 = item["box_m"]
            ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fc=color, ec="#46525C",
                                   lw=.85, zorder=2))
            name = "备餐台面" if room.get("functional") and item["name"] == "操作台" else item["name"]
            regions.append((item["box_m"], name, "#152331"))
            if "front_xy" in item:
                front = np.array(item["front_xy"])
                side = np.array([-front[1], front[0]])
                center = np.array([(x1+x2)/2, (y1+y2)/2])
                tip = center + (np.dot(np.abs(front), [(x2-x1)/2, (y2-y1)/2])-.04)*front
                base = tip - .11*front
                vertices = np.array([tip, base+.07*side, base-.07*side])
                ax.add_patch(Polygon(vertices, fc="#243A4A", ec="none", zorder=4))
                arrows.append((*vertices.min(axis=0), *vertices.max(axis=0)))
        for zone, name in zip(spec["zones"], ("门前区", "通道"), strict=True):
            x1, y1, x2, y2 = zone
            ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fc="#923D5230", ec="#923D52",
                                   lw=.7, zorder=3))
            regions.append((zone, name, "#80243C"))
        ax.add_patch(Rectangle((0, 0), width, height, fc="none", ec="#28353F", lw=1.2))
        door_left, _, door_right, _ = spec["zones"][0]
        ax.plot([door_left, door_right], [0, 0], color="#923D52", lw=2.6, solid_capstyle="butt")
        ax.annotate("门", ((door_left+door_right)/2, 0), xytext=(0, -8), textcoords="offset points",
                    ha="center", va="top", color="#80243C")
        draw_window(ax, solution)
        ax.set(xlim=(-.12, width+.12), ylim=(-.30, height+.25),
               xticks=np.arange(int(width)+1), yticks=np.arange(int(height)+1),
               xlabel="x / m", ylabel="y / m", aspect="equal")
        ax.patch.set_visible(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.canvas.draw()
        label_regions(ax, regions, fig.canvas.get_renderer(), arrows)
        stem = f"best_{room['title']}"
        fig.savefig(args.out / f"{stem}.png", dpi=600)
        fig.savefig(args.out / f"{stem}.pdf")
        fig.savefig(args.out / f"{stem}.svg")
        plt.close(fig)
        index.append(dict(room=key, title=room["title"], seed=seed, cost=cost,
                          feasible_runs=len(feasible), total_ga_runs=trials,
                          window_wall=solution["window"]["wall"],
                          window_distance_m=metrics.get("window_distance_m"),
                          window_on_sofa_side=metrics.get("window_on_sofa_side"),
                          solution=str(source), png=f"{stem}.png"))
        print(f"{room['title']}  seed={seed}  cost={cost:.10g}  feasible={len(feasible)}/{trials}")
    if index:
        with (args.out / "best_index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(index[0]))
            writer.writeheader()
            writer.writerows(index)


if __name__ == "__main__":
    main()
