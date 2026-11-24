"""为窗户版扫描位置变异概率，并保存八个场景的原始结果。"""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rate_name(rate):
    return "mutation_" + format(rate, "g").replace(".", "p")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rates", nargs="+", type=float,
                        default=[.05, .10, .20, .30, .40])
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--seed-start", type=int, default=20)
    parser.add_argument("--generations", type=int, default=200)
    parser.add_argument("--population", type=int, default=80)
    parser.add_argument("--out", default="sensitivity_results")
    parser.add_argument("--reference", default="results")
    args = parser.parse_args()
    if any(not 0 <= value <= 1 for value in args.rates):
        parser.error("rates 必须在 [0, 1] 内")
    if len(set(args.rates)) != len(args.rates):
        parser.error("rates 不能重复")
    if args.seeds < 1 or args.generations < 1 or args.population < 4:
        parser.error("seeds、generations 和 population 参数不合法")

    out = Path(args.out).resolve()
    if out.exists():
        parser.error(f"{out} 已存在，请指定新的输出目录")
    out.mkdir(parents=True)
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    rooms = ["standard", "bathroom_standard", "kitchen_standard", "living_standard",
             "compact", "bathroom_compact", "kitchen_compact", "living_compact"]
    manifest = dict(
        status="running",
        created_at=datetime.now().astimezone().isoformat(),
        parameter="GAConfig.mutation",
        meaning="每件家具和窗户位置坐标接受高斯扰动的概率；旋转概率保持 0.05",
        rates=args.rates, seeds=seeds, rooms=rooms,
        population=args.population, generations=args.generations,
        methods=["ga"], reference=str(Path(args.reference).resolve()),
        note="只改变位置变异概率；参数组共享种子、初始种群和评估预算",
    )
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    combined_runs, combined_summary, initial_by_case = [], [], {}
    started = perf_counter()
    runner = Path(__file__).with_name("run_experiments.py")
    verifier = Path(__file__).with_name("verify_results.py")
    for rate in args.rates:
        directory = out / rate_name(rate)
        command = [sys.executable, str(runner),
                   "--seeds", str(args.seeds), "--seed-start", str(args.seed_start),
                   "--generations", str(args.generations), "--population", str(args.population),
                   "--mutation", format(rate, "g"), "--rooms", *rooms,
                   "--methods", "ga", "--out", str(directory)]
        print()
        print(f"位置变异概率 p = {rate:.2f}", flush=True)
        subprocess.run(command, check=True)
        subprocess.run([sys.executable, str(verifier), "--results", str(directory)], check=True)
        meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        combined_runs.extend(dict(mutation=rate, **row)
                             for row in read_csv(directory / "runs.csv"))
        combined_summary.extend(dict(mutation=rate, **row)
                                for row in read_csv(directory / "summary.csv"))
        for room in rooms:
            for seed in seeds:
                filename = f"{room}_ga_seed{seed:02d}.json"
                result = json.loads((directory / "solutions" / filename).read_text(encoding="utf-8"))
                case = (room, seed)
                if case in initial_by_case:
                    assert result["initial"] == initial_by_case[case], f"初始布局不一致: {case}"
                else:
                    initial_by_case[case] = result["initial"]
                assert result["evaluations"] == meta["evaluations_per_run"]
        write_csv(out / "runs.csv", combined_runs)
        write_csv(out / "summary.csv", combined_summary)

    audit = dict(
        status="PASS",
        audited_runs=len(combined_runs),
        parameter_levels=len(args.rates),
        shared_initial_layout_cases=len(initial_by_case),
        checks=["每个参数组通过独立几何与评分核验",
                "五个参数组共享同一批初始布局",
                "八个场景均纳入扫描",
                "各参数组使用相同评估预算"],
    )
    (out / "verification.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest.update(status="complete", total_runs=len(combined_runs),
                    wall_seconds=perf_counter() - started)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("敏感性实验完成：", out, flush=True)
    print(json.dumps(audit, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
