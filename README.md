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

## A 题当前交付版本

本分支以队友提交 `c6e7dd5` 的完整数据与有限体积实现为底稿，叠加 BDF 事件根、显示安全裕量、长期炉况延拓、收缩域退化测试、蒸发潜热量级审计和扩散关系灵敏度复核。

从项目根目录运行快速检查：

```bash
python3 src/problem_a_pipeline_cc_v01.py --stage all --profile quick
```

正式重算、导出和验证：

```bash
python3 src/problem_a_pipeline_cc_v01.py --stage all --profile final
```

当前正式文件：

- 论文：`paper/problem_a/problem_a_paper_cc_v05.pdf`
- 论文源码：`paper/problem_a/problem_a_paper_cc_v05.tex`
- AI 使用详情：`paper/problem_a/problem_a_ai_usage_cc_v01.pdf`
- 提交工作簿：`outputs/submissions/problem_a/result1.xlsx` 至 `result4.xlsx`
- 本轮决策与审计：`docs/20260912_1435_problem_a_epic_revision_cc.md`

所有新增脚本均直接读取队友保留的 `data/raw/problem_a_raw_attachment_1_v01.xlsx` 与 `data/raw/problem_a_raw_attachment_2_v01.xlsx`，未复制或改写原始数据。
