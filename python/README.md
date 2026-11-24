# 家具与窗户联合布局优化 · Python 源码

[在线三维演示](https://hjt213.github.io/layout-optimization/)

本项目在给定矩形房间、出入口和家具尺寸的条件下，联合优化家具的位置、朝向和单扇窗户的位置。包括卧室、卫生间、厨房和客厅，每种房型有标准版和紧凑版，共 8 个仿真场景。

本目录是 Python 求解与实验复现部分。仓库根目录的 Three.js 网页读取预先导出的 `demo-data.js`，用于回放三维布局和收敛曲线，不会在浏览器中重新运行 Python。优化模型在二维平面中求解，网页中的家具高度仅用于展示。

## 建模与算法

- **混合编码：** 用连续参数表示家具位置和窗户沿墙的位置，用离散参数表示家具朝向和窗户所在墙面。组合解码器处理椅子朝向书桌、厨房台面一字排列、沙发正对电视柜等关系。
- **硬约束：** 家具不得越界、重叠或侵入门前区、预留通道和相应房型的功能净空区；窗户必须位于允许的墙面，并与墙角保持最小距离。
- **软代价：** 按房型功能关系、窗位偏好、拥挤程度和局部留白评分。例如卧室偏好窗户靠近书桌，厨房偏好窗户靠近灶台。不可行布局会受到额外惩罚。
- **算法对照：** 比较带精英保留的遗传算法（GA）、随机搜索（RS）和无变异遗传算法（GA-NoMut）。同一场景和种子下，三种方法共享初始种群及候选评估预算。

## 实验结果

主实验覆盖 8 个场景、3 种方法和 30 个随机种子（20–49），共 720 次运行。每次运行评估 15,280 个候选布局：80 个初始个体，加上 200 轮、每轮 76 个新候选。

| 方法 | 获得可行解的运行次数 | 可行率 |
| --- | ---: | ---: |
| 遗传算法 | 240 / 240 | 100% |
| 随机搜索 | 162 / 240 | 67.50% |
| 无变异遗传算法 | 191 / 240 | 79.58% |

这里的可行率指满足模型硬约束的运行比例，结果仅适用于这 8 个仿真场景和上述评估预算。

## 源码清单

| 文件 | 用途 |
| --- | --- |
| `bedroom_ga.py` | 房型定义、几何约束、代价计算和三种搜索算法；不限于卧室 |
| `functional_layout.py` | 厨房和客厅的家具组合与功能区解码 |
| `window_layout.py` | 窗户墙面与端点解码、窗位偏好评分 |
| `spatial_balance.py` | 家具拥挤和局部留白代价 |
| `run_experiments.py` | 运行主实验或小尺寸厨卫设施对照实验 |
| `run_sensitivity.py` | 运行位置变异概率敏感性实验 |
| `test_model.py`、`verify_results.py` | 单元测试及对保存结果的几何、代价和统计核验 |
| `plot_results.py`、`plot_best.py` | 绘制主实验统计图、布局对照和最佳布局 |
| `plot_room_examples.py`、`plot_sensitivity.py` | 绘制指定种子的布局，以及变异参数对照图 |
| `plot_report.py` | 将已生成的数据与图片组织为报告组合图 |
| `requirements-experiment.txt` | 实验依赖版本 |
| `sensitivity_README.md` | 敏感性实验补充说明 |

## 本地运行与复现

以下命令适用于 Windows PowerShell 和 Python 3.12。从下载或克隆的仓库根目录进入 `python/`，后续命令均在该目录执行。实验脚本不会覆盖已有的结果目录；推荐在新下载的仓库副本中运行。

```powershell
Set-Location python
py -3.12 -m pip install -r requirements-experiment.txt
py -3.12 -m unittest test_model
```

### 主实验与绘图

```powershell
py -3.12 run_experiments.py --out results
py -3.12 verify_results.py --results results
py -3.12 plot_results.py --results results --out figures
py -3.12 plot_best.py --results results --out best_figures
```

`results/` 保存逐次运行、汇总表、收敛历史和布局坐标；`figures/` 和 `best_figures/` 保存生成的图件。`verification.json` 中的 `PASS` 表示通过程序定义的核验，不代表通过统计显著性检验。

### 小尺寸厨卫设施对照（可选）

固定紧凑卫生间和紧凑厨房的房间面积，只更换指定设施的尺寸。默认进行 180 次运行。

```powershell
py -3.12 run_experiments.py --rooms bathroom_compact kitchen_compact --smaller-fixtures --out small_fixture_results
py -3.12 verify_results.py --results small_fixture_results
```

### 位置变异概率扫描（可选）

先运行主实验，再扫描 5 档位置变异概率（0.05、0.10、0.20、0.30、0.40）。默认进行 1,200 次运行；其中 `p = 0.20` 与主实验使用同样的参数和种子，不是额外的独立重复。

```powershell
py -3.12 run_sensitivity.py --reference results --out sensitivity_results
py -3.12 plot_sensitivity.py --results sensitivity_results --out sensitivity_figures
```

### 报告组合图（可选）

完成主实验、主实验绘图和位置变异概率扫描后再运行。本脚本按固定目录名读取 `results/`、`sensitivity_results/`、`figures/` 和 `best_figures/`，不会重新运行优化。它通过 Matplotlib 的依赖 Pillow 读取布局图片。

```powershell
py -3.12 plot_report.py --root . --out report_figures
```

