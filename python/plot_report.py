"""从已保存的数据和布局图生成报告组图。"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np
from PIL import Image

SCENES = [
    ("standard", "标准卧室"), ("compact", "紧凑卧室"),
    ("bathroom_standard", "标准卫生间"), ("bathroom_compact", "紧凑卫生间"),
    ("kitchen_standard", "标准厨房"), ("kitchen_compact", "紧凑厨房"),
    ("living_standard", "标准客厅"), ("living_compact", "紧凑客厅"),
]
METHODS = [("ga", "GA", "#0072B2", "-"),
           ("random", "RS", "#C34F00", "--"),
           ("ga_no_mutation", "GA-NoMut", "#575757", "-.")]
RATES = [0.05, 0.10, 0.20, 0.30, 0.40]
RATE_STYLES = [("#0072B2", "-"), ("#B25300", "--"), ("#008461", "-."),
               ("#8A4B92", ":"), ("#494949", (0, (5, 2, 1, 2, 1, 2)))]

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "font.size": 8, "axes.unicode_minus": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "svg.fonttype": "none",
})


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def read_history(path):
    grouped = defaultdict(list)
    for row in read_rows(path):
        grouped[row["room"], row["method"], int(row["seed"])].append(
            (int(row["evaluations"]), float(row["cost"])))
    return grouped


def plot_history(ax, history, room, method, color, style):
    series = np.asarray([sorted(history[room, method, s]) for s in range(20, 50)])
    x = series[0, :, 0]
    assert len(x) == 201 and x[-1] == 15280 and np.all(series[:, :, 0] == x)
    low, median, high = np.quantile(series[:, :, 1], [.25, .50, .75], axis=0)
    ax.fill_between(x, low, high, color=color, alpha=.12, linewidth=0)
    ax.plot(x, median, color=color, linestyle=style, linewidth=1.25)


def place_image(ax, path):
    with Image.open(path) as source:
        image = source.convert("RGB")
        image.thumbnail((2100, 1800), Image.Resampling.LANCZOS)
    target_ratio = ax.bbox.width / ax.bbox.height
    source_ratio = image.width / image.height
    width, height = min(1, source_ratio/target_ratio), min(1, target_ratio/source_ratio)
    ax.imshow(image, aspect="auto", extent=((1-width)/2, (1+width)/2,
                                             (1-height)/2, (1+height)/2))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_axis_off()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("报告图件"))
    args = parser.parse_args()
    root, out = args.root, args.out
    out.mkdir(parents=True, exist_ok=True)
    qa = out / "qa"
    qa.mkdir(exist_ok=True)
    history = read_history(root / "results" / "history.csv")
    rate_history = {
        rate: read_history(root / "sensitivity_results" /
                           ("mutation_" + format(rate, "g").replace(".", "p")) /
                           "history.csv")
        for rate in RATES
    }
    summary = {(row["room"], float(row["mutation"])): row
               for row in read_rows(root / "sensitivity_results" / "summary.csv")}
    paired = defaultdict(list)
    for row in read_rows(root / "results" / "paired.csv"):
        paired[row["room"], row["baseline"]].append(float(row["baseline_minus_ga"]))
    groups = [
        ("01_八场景收敛", "convergence"),
        ("02_八场景最佳布局", "best"),
        ("03_八场景变异概率与最终代价", "cost"),
        ("A1_八场景固定种子布局对照", "layout"),
        ("A2_八场景配对代价差", "paired"),
        ("B1_八场景变异概率与收敛", "sensitivity"),
        ("B2_八场景变异概率与可行率", "feasible"),
    ]
    for name, kind in groups:
        images = kind in ("best", "layout")
        fig, axes = plt.subplots(4, 2, figsize=(7.2, 8.9))
        fig.subplots_adjust(left=.035 if images else .12, right=.975, top=.925,
                            bottom=.07, wspace=.14 if images else .27,
                            hspace=.27 if images else .42)
        for i, (ax, (room, title)) in enumerate(zip(axes.flat, SCENES)):
            ax.text(0, 1.08, chr(97+i), transform=ax.transAxes, fontweight="bold",
                    ha="left", va="center", fontsize=9)
            ax.text(.5, 1.08, title, transform=ax.transAxes, ha="center", va="center")
            if images:
                path = (root / "best_figures" / f"best_{title}.png" if kind == "best"
                        else root / "figures" / f"layout_{room}.png")
                place_image(ax, path)
                continue
            ax.grid(axis="y", color="#E3E5E8", linewidth=.45)
            ax.set_axisbelow(True)
            ax.yaxis.set_major_locator(MaxNLocator(4))
            if kind == "convergence":
                for method, _, color, style in METHODS:
                    plot_history(ax, history, room, method, color, style)
                ax.axhline(1, color="#777777", linestyle=":", linewidth=.7)
            elif kind == "sensitivity":
                for rate, (color, style) in zip(RATES, RATE_STYLES):
                    plot_history(ax, rate_history[rate], room, "ga", color, style)
            elif kind == "paired":
                for j, (method, _, color, _) in enumerate(METHODS[1:]):
                    values = np.asarray(paired[room, method])
                    assert len(values) == 30
                    ax.scatter(j + np.linspace(-.13, .13, len(values)), values,
                               s=9, color=color, alpha=.7, linewidths=0)
                    ax.hlines(np.median(values), j-.20, j+.20, color="black", linewidth=1.3)
                ax.axhline(0, color="#555555", linestyle=":", linewidth=.8)
                ax.set(xlim=(-.42, 1.42), xticks=[0, 1], xticklabels=["RS − GA", "GA-NoMut − GA"])
            else:
                rows = [summary[room, p] for p in RATES]
                assert all(int(r["n"]) == 30 for r in rows)
                if kind == "cost":
                    ax.errorbar(RATES, [float(r["cost_mean"]) for r in rows],
                                yerr=[float(r["cost_sd"]) for r in rows],
                                fmt="o-", markersize=3.1, color="#0072B2", capsize=2.4)
                else:
                    ax.plot(RATES, [100 * float(r["feasible_rate"]) for r in rows],
                            "o-", color="#0072B2", markersize=3.1)
                    ax.set(ylim=(0, 110), yticks=[0, 25, 50, 75, 100])
                ax.set(xticks=RATES, xticklabels=[f"{p:.2f}" for p in RATES])
            if kind in ("convergence", "sensitivity"):
                ax.set(xlim=(0, 15600), xticks=[0, 5000, 10000, 15000])
        if not images:
            for left, right in axes:
                low = min(left.get_ylim()[0], right.get_ylim()[0])
                high = max(left.get_ylim()[1], right.get_ylim()[1])
                left.set_ylim(low, high)
                right.set_ylim(low, high)
            xlabel, ylabel = {
                "convergence": ("累计候选评估次数", "历史最优代价"),
                "sensitivity": ("累计候选评估次数", "历史最优代价"),
                "paired": ("配对比较", "最终代价差"),
                "cost": ("位置变异概率 p", "最终代价"),
                "feasible": ("位置变异概率 p", "最终可行率（%）"),
            }[kind]
            fig.supxlabel(xlabel, y=.018, fontsize=9)
            fig.supylabel(ylabel, x=.012, fontsize=9)
        if kind in ("convergence", "sensitivity"):
            specs = ([(label, color, style) for _, label, color, style in METHODS]
                     if kind == "convergence"
                     else [(f"p = {rate:.2f}", color, style)
                           for rate, (color, style) in zip(RATES, RATE_STYLES)])
            handles = [Line2D([0], [0], label=label, color=color, linestyle=style)
                       for label, color, style in specs]
            fig.legend(handles=handles, loc="upper center", ncols=len(handles),
                       frameon=False, bbox_to_anchor=(.52, .997))
        fig.canvas.draw()
        try:
            from audit_panel_alignment import require_matplotlib_panel_alignment
        except ImportError:
            pass
        else:
            require_matplotlib_panel_alignment(fig, strict=True, require_panel_labels=True,
                                               json_out=qa / f"{name}.alignment.json")
        fig.savefig(out / f"{name}.png", dpi=600)
        fig.savefig(out / f"{name}.pdf", dpi=320)
        fig.savefig(out / f"{name}.svg", dpi=320)
        plt.close(fig)
        print(name, flush=True)


if __name__ == "__main__":
    main()
