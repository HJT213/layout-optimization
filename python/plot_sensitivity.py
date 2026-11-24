"""从位置变异概率扫描结果生成三类论文图。"""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00"]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def rate_name(rate):
    return "mutation_" + format(rate, "g").replace(".", "p")


def save(fig, out, name):
    fig.savefig(out / f"{name}.png", dpi=600, bbox_inches="tight")
    fig.savefig(out / f"{name}.svg", bbox_inches="tight")
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="sensitivity_results")
    parser.add_argument("--out", default="sensitivity_figures")
    args = parser.parse_args()
    root, out = Path(args.results), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        parser.error("敏感性实验尚未完整结束")
    rates, seeds, rooms = manifest["rates"], manifest["seeds"], manifest["rooms"]
    summary = read_csv(root / "summary.csv")
    meta_path = root / rate_name(rates[0]) / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    history_cache = {}
    for rate in rates:
        history = read_csv(root / rate_name(rate) / "history.csv")
        for room in rooms:
            for seed in seeds:
                history_cache[rate, room, seed] = [
                    row for row in history if row["room"] == room and int(row["seed"]) == seed
                ]

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })

    for room in rooms:
        title = meta["rooms"][room]["title"]
        # 图 1：不同 p 的历史最优代价收敛中位数和四分位区间。
        fig, ax = plt.subplots(figsize=(8.5, 5.2), layout="constrained")
        for rate, color in zip(rates, COLORS):
            series = [[float(row["cost"]) for row in history_cache[rate, room, seed]]
                      for seed in seeds]
            values = np.asarray(series)
            history = history_cache[rate, room, seeds[0]]
            x = np.asarray([int(row["evaluations"]) for row in history])
            low, median, high = np.quantile(values, [.25, .5, .75], axis=0)
            ax.plot(x, median, color=color, lw=1.8, label=f"p = {rate:.2f}")
            ax.fill_between(x, low, high, color=color, alpha=.10, linewidth=0)
        ax.set(xlabel="累计候选布局评估次数",
               ylabel="历史最优代价 F（越低越好）",
               title=f"{title}｜不同位置变异概率的收敛曲线")
        ax.grid(alpha=.18)
        # 将多条曲线的图例放到坐标轴外，避免图例线与曲线或文字发生视觉遮挡。
        ax.legend(ncol=3, frameon=False, loc="upper center",
                  bbox_to_anchor=(0.5, -0.14), borderaxespad=0.0)
        save(fig, out, f"sensitivity_convergence_{room}")

        group = [next(row for row in summary
                      if row["room"] == room and float(row["mutation"]) == rate)
                 for rate in rates]
        x = np.asarray(rates)
        means = np.asarray([float(row["cost_mean"]) for row in group])
        sd = np.asarray([float(row["cost_sd"]) for row in group])
        # 图 2：最终代价均值和跨种子标准差。
        fig, ax = plt.subplots(figsize=(7.8, 4.8), layout="constrained")
        ax.errorbar(x, means, yerr=sd, fmt="o-", capsize=4, lw=1.8,
                    color="#0072B2", label=title)
        ax.set(xticks=rates, xlabel="每个位置坐标的变异概率 p",
               ylabel="最终代价 F（均值 ± 样本标准差）",
               title=f"{title}｜位置变异概率敏感性")
        ax.grid(alpha=.18)
        save(fig, out, f"sensitivity_cost_{room}")

        # 图 3：最终可行率。
        feasible = np.asarray([100 * float(row["feasible_rate"]) for row in group])
        fig, ax = plt.subplots(figsize=(7.8, 4.8), layout="constrained")
        ax.plot(x, feasible, "o-", lw=1.8, color="#0072B2", label=title)
        ax.set(xticks=rates, yticks=[0, 25, 50, 75, 100], ylim=(-3, 108),
               xlabel="每个位置坐标的变异概率 p",
               ylabel="最终可行解获得率 / %",
               title=f"{title}｜可行率随位置变异概率的变化")
        ax.grid(alpha=.18)
        save(fig, out, f"sensitivity_feasible_{room}")
    print("敏感性图片已保存：", out.resolve())


if __name__ == "__main__":
    main()
