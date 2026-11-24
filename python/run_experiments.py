"""运行真实实验，保存每次结果、收敛曲线、汇总与环境信息。"""
import argparse
import csv
from dataclasses import asdict, replace
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter

# 支持使用项目内的依赖目录。常规安装见 requirements-experiment.txt。
local_deps = Path(__file__).resolve().parent / ".deps"
if local_deps.exists():
    sys.path.insert(0, str(local_deps))
import numpy as np
from bedroom_ga import GAConfig, ROOMS, FURNITURE, optimize, room_spec


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=30, help="重复运行次数")
    parser.add_argument("--seed-start", type=int, default=20, help="首个种子；默认 20 到 49")
    parser.add_argument("--generations", type=int, default=200)
    parser.add_argument("--population", type=int, default=80)
    parser.add_argument("--mutation", type=float, default=0.20,
                        help="每个位置坐标的变异概率；旋转变异仍固定为 0.05")
    parser.add_argument("--rooms", nargs="+", choices=list(ROOMS), default=list(ROOMS))
    parser.add_argument("--methods", nargs="+", choices=["ga", "random", "ga_no_mutation"],
                        default=["ga", "random", "ga_no_mutation"])
    parser.add_argument("--out", default="results", help="输出新目录；拒绝覆盖已有实验")
    parser.add_argument("--smaller-fixtures", action="store_true",
                        help="仅用于紧凑厨房和卫生间，分别使用尺寸更小的设施")
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error("seeds 至少为 1")
    if len(set(args.rooms)) != len(args.rooms) or len(set(args.methods)) != len(args.methods):
        parser.error("房间和方法不能重复")
    config = GAConfig(population=args.population, generations=args.generations,
                      mutation=args.mutation)
    config.validate()
    if args.smaller_fixtures and not set(args.rooms) <= {"bathroom_compact", "kitchen_compact"}:
        parser.error("--smaller-fixtures 限于 bathroom_compact 和 kitchen_compact")
    rooms = {key: replace(ROOMS[key], functional=ROOMS[key].kind in {"living", "kitchen"},
                          smaller_fixtures=args.smaller_fixtures,
                          title=ROOMS[key].title + ("（小尺寸家具）" if args.smaller_fixtures else ""))
             for key in args.rooms}
    out = Path(args.out)
    if out.exists():
        parser.error(f"{out} 已存在，请用 --out 指定新的目录以保留原始结果")
    out.mkdir(parents=True)
    (out / "solutions").mkdir()
    metadata = dict(created_at=datetime.now().astimezone().isoformat(), config=asdict(config),
                    seeds=list(range(args.seed_start, args.seed_start + args.seeds)), methods=args.methods,
                    rooms={key: {k: v for k, v in asdict(room).items()
                                 if (k != "kind" or v != "bedroom") and
                                    (k not in {"functional", "smaller_fixtures"} or v)} for key, room in rooms.items()},
                    room_specs={key: room_spec(room) for key, room in rooms.items()},
                    furniture=[asdict(f) for f in FURNITURE],
                    environment=dict(python=sys.version, numpy=np.__version__,
                                     platform=platform.platform(), processor=platform.processor(),
                                     logical_cpus=os.cpu_count()),
                    evaluations_per_run=config.evaluations,
                    timing_note="perf_counter 测量单次优化过程，含日志记录，不含文件写入和绘图；同批次顺序运行")
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    rows, histories = [], []
    started = perf_counter()
    for room_key in args.rooms:
        for seed in metadata["seeds"]:
            for method in args.methods:
                result = optimize(rooms[room_key], config, seed, method)
                name = f"{room_key}_{method}_seed{seed:02d}.json"
                (out / "solutions" / name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                metrics = result["best"]["metrics"]
                row = dict(room=room_key, method=method, seed=seed, seconds=result["seconds"],
                           evaluations=result["evaluations"], window_wall=result["best"]["window"]["wall"],
                           window_center_x_m=result["best"]["window"]["center_m"][0],
                           window_center_y_m=result["best"]["window"]["center_m"][1], **metrics)
                rows.append(row)
                histories.extend(dict(room=room_key, method=method, seed=seed, **h)
                                 for h in result["history"])
                print(f"{room_key:8s} seed={seed:02d} {method:14s} "
                      f"cost={metrics['cost']:.6f} feasible={metrics['feasible']} "
                      f"time={result['seconds']:.3f}s", flush=True)
                # 每次运行后刷新，意外中断也保留已完成的数据。
                write_csv(out / "runs.csv", rows)
    write_csv(out / "history.csv", histories)
    summaries = []
    for room_key in args.rooms:
        for method in args.methods:
            group = [r for r in rows if r["room"] == room_key and r["method"] == method]
            costs = np.array([r["cost"] for r in group])
            feasible = [r for r in group if r["feasible"]]
            summaries.append(dict(room=room_key, method=method, n=len(group),
                                  feasible_runs=len(feasible), feasible_rate=len(feasible)/len(group),
                                  cost_mean=float(costs.mean()),
                                  cost_sd=float(costs.std(ddof=1)) if len(group)>1 else 0.0,
                                  cost_median=float(np.median(costs)),
                                  cost_min=float(costs.min()), cost_max=float(costs.max()),
                                  feasible_soft_mean=float(np.mean([r["soft"] for r in feasible])) if feasible else None,
                                  time_mean=float(np.mean([r["seconds"] for r in group])),
                                  violation_mean_m2=float(np.mean([r["violation_m2"] for r in group]))))
    write_csv(out / "summary.csv", summaries)
    # 配对比较以相同初始种群为依据；不把跨随机种子的 SD 说成置信区间。
    paired = []
    for room_key in args.rooms:
        for method in args.methods:
            if method == "ga" or "ga" not in args.methods:
                continue
            for seed in metadata["seeds"]:
                a = next(r for r in rows if r["room"]==room_key and r["seed"]==seed and r["method"]=="ga")
                b = next(r for r in rows if r["room"]==room_key and r["seed"]==seed and r["method"]==method)
                paired.append(dict(room=room_key, baseline=method, seed=seed,
                                   baseline_minus_ga=b["cost"]-a["cost"]))
    if paired:
        write_csv(out / "paired.csv", paired)
    metadata["experiment_wall_seconds"] = perf_counter() - started
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已保存：", out.resolve())
    for summary in summaries:
        print(summary)


if __name__ == "__main__":
    main()
