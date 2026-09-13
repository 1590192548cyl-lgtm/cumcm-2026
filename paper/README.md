# 论文 LaTeX 工程说明

## 当前正式版本

经数据源锁定、事件定位、网格收敛、长期边界、收缩反事实与蒸发潜热审计后的正式版本为：

- `problem_a/problem_a_paper_cc_v05.tex`
- `problem_a/problem_a_paper_cc_v05.pdf`
- `problem_a/problem_a_ai_usage_cc_v01.tex`
- `problem_a/problem_a_ai_usage_cc_v01.pdf`

正式数值基线为提交 `c6e7dd5` 保存的全隐式有限体积数组；后续 BDF 结果仅作独立复核。`main.tex`、`paper.html` 与原有 `figures/`、`tables/` 保留为历史基线工程，便于比较和回退，不再作为当前提交入口。正式论文从仓库根目录编译时，应使用 XeLaTeX 或 Tectonic，并保持 `outputs/figures/` 的相对路径不变。

## 文件结构

```
paper/
├─ main.tex              正文（唯一入口）
├─ figures/              插图，PDF 与 PNG 各一份
│  ├─ fig1_p1_profile    问题 1 径向分布
│  ├─ fig2_p2_profile    问题 2 径向分布
│  ├─ fig3_p3            问题 3 时间演化与剖面
│  ├─ fig4_p4            问题 4 半径路径与含水率
│  └─ fig5_verification  模型检验三联图
└─ tables/               表格，由结果文件自动生成
   ├─ table_01_p1_temperature / table_02_p1_moisture   表 1、表 2
   ├─ table_03_p2_temperature / table_04_p2_moisture   表 3、表 4
   ├─ table_05_p3_moisture              表 5
   └─ table_06_p4_moisture              表 6
```

## 在 Overleaf 上使用

1. Overleaf 首页 → New Project → Upload Project，上传 `outputs/submissions/submission_review_20260913_1215_v03.zip`。
2. 打开后进 Menu → Compiler，选 **XeLaTeX**（文档用了 ctex 宏包，pdfLaTeX 编译中文会报错）。
3. 若目录名 `figures/` 被改动，需要同步修改 `main.tex` 里的 `\graphicspath`。

正式源码已经使用 Tectonic 编译，并对 16 页 PDF 作了逐页渲染检查。

## 图表如何重新生成

主结果图由脚本从 `c6e7dd5` 保存的未舍入数组直接生成，不手抄数字：

```bash
python3 src/visualization/problem_a_07_publication_figures_cc_v01.py
```

数据来源：

| 图表 | 来源 |
|---|---|
| 问题 1 主图、表 1、表 2 | `outputs/results/problem_a_result_08_fields_p1_v01.npz` |
| 问题 2 主图、表 3、表 4 | `outputs/results/problem_a_result_09_fields_p2_3h_v01.npz` |
| 问题 3 主图、表 5 | `outputs/results/problem_a_result_10_fields_p3_v01.npz` |
| 问题 4 主图、表 6 | `outputs/results/problem_a_result_11_fields_p4_v01.npz` |
| 审计图 | `outputs/results/` 与 `outputs/tables/` 中标注为审计、灵敏度或反事实的结果 |

## 与提交文件的对应关系

| 论文中 | 提交文件 |
|---|---|
| 表 1、表 2 | `outputs/submissions/problem_a/result1.xlsx`（1800 行 × 21 列） |
| 表 3、表 4 | `outputs/submissions/problem_a/result2.xlsx`（完整烘干过程，每 1 s；正文仅取前 3 h） |
| 表 5 | `outputs/submissions/problem_a/result3.xlsx`（每 60 s 至 $205980\,\mathrm{s}$） |
| 表 6 | `outputs/submissions/problem_a/result4.xlsx`（每 60 s 至 $183120\,\mathrm{s}$，末列为药材表面） |

## 写作约定

正文按“假设—模型—离散—结果—检验—评价”组织。问题 1--4 的正式数值取自 `c6e7dd5` 保存的未舍入数组；后续 BDF、灵敏度与潜热结果均明确作为复核或诊断，不替换正式数值。
未在文中出现的中间量（如迭代次数、网格编号）一律不给，避免堆砌。
