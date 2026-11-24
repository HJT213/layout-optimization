# 窗户版本：位置变异概率敏感性实验

本实验只改变遗传算法的位置变异概率 `p`，其余设置保持一致，用于分析参数对收敛、最终代价和可行率的影响。

- 场景：`standard`、`bathroom_standard`、`kitchen_standard`、`living_standard`、`compact`、`bathroom_compact`、`kitchen_compact`、`living_compact`
- 位置变异概率：`0.05`、`0.10`、`0.20`、`0.30`、`0.40`
- 随机种子：`20–49`，每个参数组 30 次
- 种群规模：80；迭代代数：200
- 总运行次数：1200
- 公平性控制：各参数组共享相同的初始布局和评估预算

每个场景有三类统计图：

1. `sensitivity_convergence_<场景>`：不同 `p` 下的历史最优代价收敛曲线；曲线为 30 次运行的中位数，阴影为四分位区间。
2. `sensitivity_cost_<场景>`：最终代价均值及跨种子样本标准差。
3. `sensitivity_feasible_<场景>`：最终可行解获得率。

图表同时导出为 PNG、PDF 和 SVG。原始运行记录在 `sensitivity_results/`，汇总表为 `summary.csv`，完整核验结果为 `verification.json`。
