# 2026 全国大学生数学建模竞赛协作仓库

本仓库用于三人团队在比赛期间统一管理代码、数据、图表、论文材料和提交版本。

## 目录结构

```text
.
├── data/
│   ├── raw/          # 题目原始数据，只读、不覆盖
│   ├── interim/      # 清洗或转换中的中间数据
│   └── processed/    # 可直接建模的最终数据
├── src/
│   ├── preprocessing/# 数据清洗与特征工程
│   ├── models/       # 模型代码
│   ├── analysis/     # 统计分析、敏感性与稳健性检验
│   └── visualization/# 绘图代码
├── notebooks/        # 探索性分析；正式结果应沉淀到 src
├── outputs/
│   ├── figures/      # 论文图
│   ├── tables/       # 论文表
│   ├── results/      # 模型结果与日志
│   └── submissions/  # 阶段性提交包与最终提交包
├── docs/             # 思路、分工、会议记录、论文草稿说明
├── references/       # 允许共享的参考资料或其索引
├── FILE_NAMING_CONVENTION.md
└── CONTRIBUTING.md
```

## 比赛开始前

1. 三人都安装 Git，并配置自己的姓名和邮箱。
2. 克隆仓库后阅读 `FILE_NAMING_CONVENTION.md` 与 `CONTRIBUTING.md`。
3. 原始题目和数据只放入 `data/raw/`，禁止直接修改。
4. 密钥、账号、个人隐私、超大数据文件不要提交。

## 常用命令

```bash
git pull --rebase origin main
git switch -c feat/你的任务
git add 路径
git commit -m "feat: 简要说明"
git push -u origin feat/你的任务
```

紧急比赛节奏下仍建议通过 Pull Request 合并；至少由另一位队员快速检查后再合并到 `main`。

## A 题计算

从项目根目录运行：

```bash
python3 src/models/problem_a_01_preheat_pde_cc_v01.py
python3 src/models/problem_a_03_full_drying_pde_cc_v01.py
```

前一条命令计算问题 1，后一条命令计算问题 2 至问题 4。机器可读结果写入 `outputs/results/`，论文表格写入 `outputs/tables/`，图片写入 `outputs/figures/`。按题目模板生成的 `result1.xlsx` 至 `result4.xlsx` 位于 `outputs/submissions/problem_a/`。

完整模型、长期炉况外推假设和论文表 1 至表 6 的数值见 `docs/20260910_2000_problem_a_full_solution_cc.md`。
