"""从保存的实验数据重绘图片，不重新优化、不调用 API。"""
import argparse
import csv
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
if (ROOT / ".deps").exists():
    sys.path.insert(0, str(ROOT / ".deps"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "none", "pdf.fonttype": 42,
})
METHODS = {"ga": "遗传算法 GA", "random": "随机搜索 RS", "ga_no_mutation": "无变异 GA"}
COLORS = {"ga": "#0072B2", "random": "#D55E00", "ga_no_mutation": "#777777"}
FURN_COLORS = ["#91BED4", "#C7B2D8", "#E9C88B", "#A8C9A5", "#E0B3A6", "#B8BFD0"]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig, directory, name):
    fig.savefig(directory / f"{name}.png", dpi=600, bbox_inches="tight")
    fig.savefig(directory / f"{name}.svg", bbox_inches="tight")
    fig.savefig(directory / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def draw_window(ax, solution, legacy_window=None):
    window = solution.get("window")
    if window is None and isinstance(legacy_window, (tuple, list)) and len(legacy_window) == 3:
        left, right, y = legacy_window
        window = dict(wall="opposite", endpoints_m=((left, y), (right, y)),
                      center_m=((left+right)/2, y))
    if not window:
        return
    a, b = window["endpoints_m"]
    right = window["wall"] == "right"
    ax.plot((a[0], b[0]), (a[1], b[1]), color="#057487", lw=3.6,
            solid_capstyle="butt", zorder=6, clip_on=False)
    ax.annotate("窗", window["center_m"], textcoords="offset points",
                xytext=(5, 0) if right else (0, 4),
                ha="left" if right else "center", va="center" if right else "bottom",
                color="#057487", fontsize=9, zorder=7, annotation_clip=False)


def window_note(solution):
    metrics = solution["metrics"]
    wall = "右墙" if solution["window"]["wall"] == "right" else "门对面墙"
    if "window_distance_m" in metrics:
        return f"{wall} · 至目标中心 {metrics['window_distance_m']:.2f} m"
    side = "沙发侧墙" if metrics["window_on_sofa_side"] else "沙发前后墙"
    return f"{wall} · {side}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="figures")
    parser.add_argument("--example-seed", type=int, default=20,
                        help="固定展示种子，避免按效果挑选")
    parser.add_argument("--skip-layout", action="store_true", help="仅绘制统计图")
    args = parser.parse_args()
    source, out = Path(args.results), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    histories = read_csv(source / "history.csv")
    runs = read_csv(source / "runs.csv")
    methods, seeds = metadata["methods"], metadata["seeds"]
    if (not args.skip_layout and {"ga", "random"} <= set(methods)
            and args.example_seed in seeds):
        from plot_room_examples import main as plot_examples
        plot_examples(["--results", str(source), "--out", str(out),
                       "--seed", str(args.example_seed)])
    histories_by_case = {}
    for row in histories:
        case = (row["room"], row["method"], int(row["seed"]))
        histories_by_case.setdefault(case, []).append(row)
    for key in metadata["rooms"]:
        title = metadata["rooms"][key]["title"]
        fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
        for method in methods:
            data = [histories_by_case[key, method, seed] for seed in seeds]
            values = np.array([[float(r["cost"]) for r in rows] for rows in data])
            x = np.array([int(r["evaluations"]) for r in data[0]])
            low, med, high = np.quantile(values, [.25, .5, .75], axis=0)
            ax.plot(x, med, color=COLORS[method], label=METHODS[method], lw=2)
            ax.fill_between(x, low, high, color=COLORS[method], alpha=.16, linewidth=0)
        ax.axhline(1, color="#444444", linestyle=":", lw=1, label="可行解代价上界 1")
        ax.set(xlabel="累计候选布局评估次数", ylabel="历史最优代价（越低越好）",
               title=f"{title}：{len(seeds)} 次运行的中位数与四分位区间")
        ax.grid(alpha=.2)
        ax.legend(fontsize=9, loc="lower center", bbox_to_anchor=(.5, -0.28), ncols=4,
                  frameon=False)
        save(fig, out, f"convergence_{key}")

        if "ga" not in methods or len(methods)<2:
            continue
        fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
        ga = {int(r["seed"]): float(r["cost"]) for r in runs if r["room"]==key and r["method"]=="ga"}
        for index, method in enumerate(m for m in methods if m!="ga"):
            baseline = {int(r["seed"]): float(r["cost"]) for r in runs if r["room"]==key and r["method"]==method}
            differences = np.array([baseline[s]-ga[s] for s in seeds])
            # 确定性横向展开，避免点遮挡；不改动纵坐标数值。
            jitter = np.linspace(-.15, .15, len(seeds))
            ax.scatter(index+jitter, differences, c=COLORS[method], alpha=.7, s=25,
                       label=f"相对{METHODS[method]}（{np.sum(differences>0)}/{len(seeds)} 次为正）")
            ax.hlines(np.median(differences), index-.22, index+.22, color="black", lw=2)
        ax.axhline(0, color="#444444", linestyle="--", lw=1)
        ax.set(xticks=list(range(len(methods)-1)),
               xticklabels=[METHODS[m] for m in methods if m!="ga"],
               ylabel="基线代价 − GA 代价（正值表示 GA 更好）",
               title=f"{title}：按相同初始种群配对的最终差值")
        ax.grid(axis="y", alpha=.2)
        ax.legend(fontsize=9, loc="lower center", bbox_to_anchor=(.5, -0.24), ncols=2,
                  frameon=False)
        save(fig, out, f"paired_{key}")
    print("图已保存：", out.resolve())


if __name__ == "__main__":
    main()
