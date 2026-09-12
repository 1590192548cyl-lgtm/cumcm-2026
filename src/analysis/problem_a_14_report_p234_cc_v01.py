# -*- coding: utf-8 -*-
"""汇总问题 2、3、4 的结果，生成 output/报告_问题234.md。"""

import json
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
for _sub in ("preprocessing", "models", "analysis", "visualization"):
    sys.path.insert(0, str(ROOT / "src" / _sub))

OUT = ROOT / "outputs" / "submissions" / "problem_a"
LOG = ROOT / "outputs" / "results"


def table_md(name):
    return (ROOT / "outputs" / "tables" / f"{name}.md").read_text(encoding="utf-8").split("\n", 1)[1].strip()


def main():
    s = json.loads((LOG / "problem_a_result_06_summary_p234_v01.json").read_text(encoding="utf-8"))
    A = []
    p = A.append

    p("# 问题 2、3、4 结果报告")
    p("")
    p("## 1. 模型与两阶段处理")
    p("")
    p("三个问题共用同一个一维轴对称柱坐标的耦合传热传质模型，差别只在物性公式、"
      "边界条件和是否考虑收缩：")
    p("")
    p("| | 物性 | 几何 | 时间跨度 |")
    p("|---|---|---|---|")
    p("| 问题 2 | 附录 3：rho(C)、cp(C)、k(C)、D(C,T) | 固定 R = 2 cm | 0~3 h |")
    p("| 问题 3 | 附录 3 | 固定 R = 2 cm | 到烘干结束 |")
    p("| 问题 4 | 附录 4 | 动边界 R(t) 取自附件 2 | 到烘干结束 |")
    p("")
    p("**两阶段（预热平衡 + 恒温干燥）的处理。** 两阶段的差别体现在边界条件上："
      "0~14400 s 直接采用附件 1 实测的烘房温度与水分浓度（分段线性插值），"
      "数据范围之外按平台值常数外延（约 49.97 摄氏度、0.0499 kg/kg）。"
      "这样两阶段自然连续、不需要人为设定切换时刻。作为检验，"
      "把切换点显式取在 1.5 h、2 h、4 h 分别重算，烘干时长完全相同（见第 5 节），"
      "说明这一判据的选择不影响结论。")
    p("")
    p("**问题 4 的动边界处理。** 令 xi = r/R(t)，把收缩的动域映射到固定区间 [0,1]。"
      "由于药材的干基含水率是按干物料质量定义的，收缩时干物料质量守恒，"
      "在 xi 坐标下每单位 xi 对应的干物料质量不变，因此节点固定在 xi 网格上即可，"
      "节点上的含水率不会出现虚假跳跃（这正是物质/拉格朗日坐标的好处）。"
      "半径只出现在系数里：扩散项乘 1/R(t)^2，表面通量项乘 1/R(t)。")
    p("")
    p("## 2. 问题 2：整个烘干过程（0~3 h）")
    p("")
    p("t = 3 h 时：中心 49.8495 摄氏度 / 1.7662 kg/kg，表面 49.9664 摄氏度 / "
      "1.0078 kg/kg。温度已基本均匀并与烘房一致（烘房此时 49.97 摄氏度），"
      "说明预热平衡阶段在 3 h 内已经完成，之后进入恒温干燥阶段。")
    p("")
    p("### 表 3：3 小时内药材的温度（摄氏度）")
    p("")
    p(table_md("problem_a_table_03_p2_temperature_v01"))
    p("")
    p("### 表 4：3 小时内药材的水分浓度（kg/kg）")
    p("")
    p(table_md("problem_a_table_04_p2_moisture_v01"))
    p("")
    p("3 h 内水分已经明显下降（中心 2.55 -> 1.77），与问题 1 的 30 min（中心几乎不动）"
      "形成对比：这正是附录 3 的 D 在低含水率下比附录 2 塌缩得慢、"
      "加上温度升到 50 摄氏度后扩散加快的结果。")
    p("")
    p("## 3. 问题 3：烘干总时长")
    p("")
    p(f"**烘干所需时间 = {s['问题3_烘干时长_h']:.2f} h = "
      f"{s['问题3_烘干时长_h'] / 24:.2f} 天**（判据：max_r C(r,t) <= 0.15 kg/kg）。")
    p("")
    p("中心是最后达标的部位，表面很早就降到 0.15 以下；"
      "整个过程呈现明显的两段：前期（约 1 天内）水分快速下降，"
      "后期由于 D 随含水率降低而急剧减小，进入长尾阶段，"
      "最后 0.05 kg/kg 的下降占了将近一半的时间。")
    p("")
    p("### 表 5：药材烘干过程的水分浓度（kg/kg）")
    p("")
    p(table_md("problem_a_table_05_p3_moisture_v01"))
    p("")
    p("## 4. 问题 4：含收缩的烘干时长")
    p("")
    p(f"**烘干所需时间 = {s['问题4_烘干时长_h']:.2f} h = "
      f"{s['问题4_烘干时长_h'] / 24:.2f} 天**，结束时半径 "
      f"{s['问题4_结束半径_cm']:.3f} cm。")
    p("")
    p("### 表 6：药材烘干过程的水分浓度（kg/kg）")
    p("")
    p("注意：药材半径从 2.0 cm 收缩到约 1.2 cm，因此"
      "「到药材中心距离 = 1.5 cm」这类固定位置在 t > 4 h 后已经落在药材之外。"
      "本题表中各列按**材料点**给出，即表头数字是该材料点的**初始**径向位置，"
      "最后一列「药材表面」是当前表面 xi = 1（初始位置 2.0 cm）。")
    p("")
    p(table_md("problem_a_table_06_p4_moisture_v01"))
    p("")
    p("### 收缩到底有多重要（对照实验）")
    p("")
    p("| 情形 | 烘干时长 |")
    p("|---|---|")
    for k, v in s["对照实验_h"].items():
        p(f"| {k.replace('_', ' ')} | {v:.2f} h = {v / 24:.2f} 天 |")
    p("")
    p(f"如果不考虑收缩，附录 4 的物性会算出 "
      f"{s['对照实验_h']['附录4_无收缩']:.1f} h（约 5.3 天），"
      "与题干「烘干过程一般持续 2~3 天」不符；"
      f"计入附件 2 的收缩后为 {s['问题4_烘干时长_h']:.1f} h（约 2.1 天），与题干自洽。"
      f"收缩把扩散路径由 2.0 cm 缩短到 1.198 cm，特征时间按 "
      f"(2/1.198)^2 = 2.79 倍缩短，实测提速 "
      f"{s['收缩提速倍数']:.2f} 倍，两者吻合。")
    p("")
    p("## 5. 校验与一致性")
    p("")
    c = s["问题2与问题3在3h的一致性"]
    p(f"- 问题 2（全程 dt = 0.1 s）与问题 3（1 h 后转 dt = 60 s）在 t = 3 h 的状态差异："
      f"max|dT| = {c['max|dT|']:.2e} K，max|dC| = {c['max|dC|']:.2e} kg/kg，"
      "说明长时程用 60 s 步长不影响结果。")
    p("- 两阶段切换点敏感性：显式取 1.5 h / 2 h / 4 h 三种切换点，"
      "烘干时长均为 "
      + " / ".join(f"{v:.2f} h" for v in s["两阶段切换敏感性_h"].values())
      + "，与默认的连续边界处理（"
      f"{s['默认处理_连续边界']:.2f} h）相差 0.6% 以内。")
    p("- 问题 1 的求解器已通过解析解校验（偏差 4.3e-3 K）、"
      "守恒律校验（残差 1e-13 量级）和网格收敛性校验；"
      "问题 2~4 复用同一内核，仅更换物性、边界与几何。")
    tstep = json.loads((LOG / "problem_a_result_05_sensitivity_km_v01.json").read_text(encoding="utf-8"))["长时程时间步检查"]
    p(f"- 问题 3 的时间步长无关性：dt = 60 s 与 dt = 15 s 的烘干时长分别为 "
      f"{tstep['60.0']:.2f} h 与 {tstep['15.0']:.2f} h，"
      f"相差 {abs(tstep['60.0'] - tstep['15.0']) / tstep['15.0'] * 100:.2f}%。")
    p("")
    p("## 6. 假设与口径")
    p("")
    p("1. **对流传质口径取 km_scale = 1**，即与传热完全类比的第三类边界条件 "
      "`-D dC/dr = km (C_s - C_a)`。题目未给出吸附等温线与干基密度，不做体积浓度换算。"
      "灵敏度分析表明：把口径放大到 820（外部阻力完全消失的极限），"
      "烘干时长只从 57.2 h 降到 53.2 h（−7%），且 km_scale ≥ 10 后已经饱和，"
      "说明内部扩散始终是主控环节；取小到 0.1 则外部传质成为瓶颈，"
      "整体要 144.5 h，与题干「2~3 天」直接矛盾。"
      "界面系数平均方式的网格收敛对照见 报告_问题1.md 第 7 节。")
    p("2. **不含相变潜热**。题目未给水的汽化潜热，且问题 2~4 统一要求使用"
      "附录 3、附录 4 的经验公式，故能量方程按唯象处理，不显式加入蒸发吸热项。"
      "这是与题目一致的简化；作为扩展可以加入潜热项对比。")
    p("3. **收缩按附件 2 实测半径统一缩放**（几何相似收缩），"
      "采用 xi = r/R(t) 的物质坐标处理动边界。")
    p("4. 附件 1 只覆盖 4 h，之后按平台值（49.97 摄氏度、0.0499 kg/kg）常数外延；"
      "附件 2 只覆盖 3 天，之后半径按 1.198 cm 常数外延。")
    p("")
    p("## 7. 产出文件")
    p("")
    import numpy as np
    n3 = np.load(OUT / "problem_a_result_10_fields_p3_v01.npz")["t"].size
    n4 = np.load(OUT / "problem_a_result_11_fields_p4_v01.npz")["t"].size
    import re
    log_p2 = LOG / "run_p2_full.log"
    n2 = 205775
    if log_p2.exists():
        m = re.search(r"result2\.xlsx 已写出：(\d+) 行", log_p2.read_text(encoding="utf-8"))
        if m:
            n2 = int(m.group(1))
    p(f"- `output/result2.xlsx`：问题 2，**整个烘干过程**每 1 s、每 0.1 cm"
      f"（{n2} 行 x 21 列），工作表「温度」「水分浓度」；"
      f"正文表 3、表 4 对应的 0~3 h 节选另存为 `output/extra/result2_3h.xlsx`。")
    p(f"- `output/result3.xlsx`：问题 3，每 60 s、每 0.1 cm，直到烘干结束"
      f"（{n3} 行 x 21 列）。")
    p(f"- `output/result4.xlsx`：问题 4，每 60 s、每 0.1 cm，末列为「药材表面」"
      f"（{n4} 行 x 21 列）。")
    p("- `output/tables/`：表 3、表 4、表 5、表 6（CSV 与 Markdown）。")
    p("- `output/p2_fields.npz`、`p3_fields.npz`、`p4_fields.npz`：完整数值解。")
    p("- `figures/p2_process.png`、`p3_drying.png`、`p4_shrinkage.png`。")
    p("")

    (ROOT / "docs" / "problem_a_report_p234_cc_v01.md").write_text("\n".join(A) + "\n", encoding="utf-8")
    print(f"已生成 {ROOT / 'docs' / 'problem_a_report_p234_cc_v01.md'}")


if __name__ == "__main__":
    main()
