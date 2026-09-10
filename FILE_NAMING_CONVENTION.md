# 文件与结果命名规范

目标：看到文件名就知道“题号、模块、内容、作者、版本”，并保证 Windows、macOS、Linux 均可正常使用。

## 1. 通用规则

- 文件名统一使用小写英文、数字和下划线 `_`。
- 不使用空格、中文、括号或特殊符号；扩展名保持小写。
- 日期统一为 `YYYYMMDD`，时间统一为 `HHMM`（24 小时制）。
- 题号统一为 `problem_a`、`problem_b`、`problem_c`、`problem_d`、`problem_e`。
- 阶段版本统一为 `v01`、`v02`、……，禁止使用 `最终版`、`最终版2`、`最新版`。
- 人员标识使用三人约定的 2–8 位英文 ID，例如 `cc`、`alice`、`bob`。
- 同一分析的代码、图、表尽量共享同一个 `topic`，方便检索。

## 2. 标准格式

代码文件：

```text
<题号>_<模块序号>_<topic>_<作者>_v<版本>.<扩展名>
```

示例：

```text
problem_a_01_clean_data_cc_v01.py
problem_a_02_baseline_model_alice_v03.py
problem_a_03_sensitivity_bob_v02.m
```

数据文件：

```text
<题号>_<阶段>_<topic>_v<版本>.<扩展名>
```

其中阶段只用 `raw`、`interim`、`processed`：

```text
problem_a_raw_attachment_1_v01.xlsx
problem_a_interim_city_panel_v02.csv
problem_a_processed_model_input_v01.csv
```

图表和结果：

```text
<题号>_<figure|table|result>_<编号>_<topic>_v<版本>.<扩展名>
```

示例：

```text
problem_a_figure_01_trend_comparison_v02.png
problem_a_table_03_robustness_checks_v01.xlsx
problem_a_result_02_model_metrics_v04.csv
```

会议记录、思路与论文材料：

```text
<YYYYMMDD>_<HHMM>_<topic>_<作者>.md
```

示例：

```text
20260910_1830_problem_selection_team.md
20260911_0215_model_revision_cc.md
```

提交包：

```text
submission_<阶段>_<YYYYMMDD>_<HHMM>_v<版本>.<扩展名>
```

其中阶段使用 `checkpoint`、`review` 或 `final`：

```text
submission_review_20260912_1400_v03.zip
submission_final_20260913_1930_v01.zip
```

## 3. 代码内部输出规则

- 所有脚本只从项目根目录下的相对路径读写，不写个人电脑绝对路径。
- 正式代码不得覆盖 `data/raw/` 中的任何文件。
- 图保存到 `outputs/figures/`，表保存到 `outputs/tables/`，数值结果和日志保存到 `outputs/results/`。
- 随机模型必须显式固定随机种子，并在代码注释或运行日志中记录。
- 关键结果应同时保存为机器可读格式（如 CSV）和论文使用格式（如 PNG、PDF 或 XLSX）。

## 4. 禁止示例

```text
新建文件夹/
最终结果.xlsx
代码最新版2.py
图(1).png
小王修改后的模型.py
```

## 5. 三人开赛时要立即确定的值

- 参赛题号：`problem_?`
- 三人的英文 ID
- 主力语言及版本，例如 Python 3.12 / R 4.5 / MATLAB R2026a
- 统一随机种子，例如 `20260910`

