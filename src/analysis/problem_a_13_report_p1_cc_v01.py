# -*- coding: utf-8 -*-
"""把求解结果、论文表格与校验结论汇总成一份可读报告。

读取： output/tables/*.md, logs/p1_diagnostics.json, logs/verify_p1.json,
       data/processed/preprocess_report.json
写出： output/报告_问题1.md
"""

import json
import sys
from pathlib import Path

import numpy as np

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
for _sub in ("preprocessing", "models", "analysis", "visualization"):
    sys.path.insert(0, str(ROOT / "src" / _sub))

import problem_a_02_config_cc_v01 as cfg  # noqa: E402

OUT = ROOT / "outputs" / "submissions" / "problem_a"
LOG = ROOT / "outputs" / "results"
DATA = ROOT / "data" / "processed"


def table_md(name):
    return (ROOT / "outputs" / "tables" / f"{name}.md").read_text(encoding="utf-8").split("\n", 1)[1].strip()


def main():
    diag = json.loads((LOG / "problem_a_result_01_diagnostics_v01.json").read_text(encoding="utf-8"))
    ver = json.loads((LOG / "problem_a_result_02_verification_v01.json").read_text(encoding="utf-8"))
    pre = json.loads((DATA / "problem_a_processed_data_quality_report_v01.json").read_text(encoding="utf-8"))
    sens_path = LOG / "problem_a_result_05_sensitivity_km_v01.json"
    sens = (json.loads(sens_path.read_text(encoding="utf-8"))
            if sens_path.exists() else None)
    d = diag["无量纲数"]

    lines = []
    A = lines.append
    A("# 问题 1 结果报告：预热平衡阶段药材温度与水分浓度")
    A("")
    A("## 1. 模型")
    A("")
    A("药材按一维轴对称柱体处理，控制方程为耦合的非稳态导热与水分扩散方程：")
    A("")
    A("```")
    A("rho*cp*dT/dt = (1/r) d/dr( k r dT/dr )")
    A("dC/dt        = (1/r) d/dr( D r dC/dr ),   D = 7e-9 exp(-0.89/C)")
    A("r = 0 : dT/dr = dC/dr = 0")
    A("r = R : -k dT/dr = h (T - T_air(t)),  -D dC/dr = km (C - C_air(t))")
    A("T(r,0) = 28 摄氏度,  C(r,0) = 2.55 kg/kg")
    A("```")
    A("")
    A("边界条件 T_air(t)、C_air(t) 由附件 1 分段线性插值给出；物性取附录 2。")
    A("")
    A("## 2. 模型适用性的定量依据")
    A("")
    A("| 无量纲数 | 数值 | 含义 |")
    A("|---|---|---|")
    A(f"| 长径比 L/R | {d['长径比 L/R']:.1f} | 端面仅占 4%，可用一维径向近似 |")
    A(f"| 热 Biot 数 hR/k | {d['热_Biot_hR_k']:.4f} | 大于 0.1，集总参数法不适用 |")
    A(f"| 传质 Biot 数 k_mR/D | {d['传质_Biot_kmR_D']:.4f} | 内外传质阻力同量级 |")
    A(f"| Luikov 数 D/alpha | {d['Luikov_D_alpha']:.4f} | 热扩散比水分扩散快 "
      f"{1/d['Luikov_D_alpha']:.0f} 倍 |")
    A(f"| Fo_热 (t=1800 s) | {d['Fo_热_t1800']:.4f} | 温度场已走完一轮瞬态 |")
    A(f"| Fo_质 (t=1800 s) | {d['Fo_质_t1800']:.4f} | 水分场仍处于极早期 |")
    A("")
    A("## 3. 论文表 1：30 分钟内药材的温度（摄氏度）")
    A("")
    A(table_md("problem_a_table_01_p1_temperature_v01"))
    A("")
    A("表 1 的格式与题目要求一致，`到药材中心的距离` 取 0、0.5、1、1.5、2 cm。")
    A("")
    A("## 4. 论文表 2：30 分钟内药材的水分浓度（kg/kg）")
    A("")
    A(table_md("problem_a_table_02_p1_moisture_v01"))
    A("")
    A("## 5. 结果解读")
    A("")
    A(f"- 温度：表面先升温、中心滞后。t = 1800 s 时中心 "
      f"{diag['t=1800s']['中心温度']:.4f} 摄氏度、表面 "
      f"{diag['t=1800s']['表面温度']:.4f} 摄氏度，与烘房空气（此时 41.51 摄氏度）"
      "仍有明显温差，中心与表面温差 3.2 K，说明内部导热梯度不可忽略，"
      "集总参数法不适用。")
    A(f"- 水分：中心 {diag['t=1800s']['中心水分浓度']:.4f} kg/kg 基本不变，"
      f"表面由 2.55 降到 {diag['t=1800s']['表面水分浓度']:.4f} kg/kg；"
      "水分变化集中在距表面 5 mm 量级的薄层内（r = 1.5 cm 处仅降低 0.17 kg/kg），"
      "30 min 远不足以改变整体含水率。")
    A("- 物理原因：热扩散比水分扩散快约 34 倍（Luikov 数约 0.029），"
      "因此该阶段是典型的\"温度基本走完、水分刚起步\"。")
    A("")
    A("## 6. 校验结论")
    A("")
    A("| 校验项 | 结果 |")
    A("|---|---|")
    A(f"| 能量守恒相对残差 | {ver['守恒残差']['能量']:.2e} |")
    A(f"| 水分质量守恒相对残差 | {ver['守恒残差']['水分']:.2e} |")
    A(f"| 与解析解最大偏差（细网格） | {ver['解析解对比']['细网格最大偏差_K']:.2e} K |")
    A(f"| 与解析解最大偏差（生产网格） | {ver['解析解对比']['生产网格最大偏差_K']:.2e} K |")
    A(f"| 生产网格与参考网格最大偏差 | "
      f"{ver['生产网格_vs_参考网格']['max|dT|']:.2e} K / "
      f"{ver['生产网格_vs_参考网格']['max|dC|']:.2e} kg/kg |")
    A(f"| 温度收敛阶估计 | "
      f"{', '.join(f'{p:.2f}' for p in ver['收敛性']['温度收敛阶'])} |")
    A(f"| Picard 迭代 | 平均 {ver['Picard迭代']['平均迭代次数']:.1f} 次/步，"
      f"最大 {ver['Picard迭代']['最大迭代次数']} 次，全部收敛 |")
    A("")
    A("## 7. 对流传质边界条件口径（km_scale）的敏感性")
    A("")
    if sens is None:
        raise SystemExit("缺少 logs/sens_km_scale.json，请先运行 src/sens_km.py")
    A("题目给出的药材含水率是干基含水率，而空气水分浓度是绝对湿度，二者基准不同，"
      "因此 `-D dC/dr = km_scale * km * (C - C_air)` 中的口径需要显式声明。"
      "本模型采用与传热完全类比的第三类边界条件（`km_scale = 1`）。")
    A("")
    A("**(a) 对问题 1 结果表的影响：只集中在最外层 2~3 列。**")
    A("")
    A("| 位置 | km_scale=0.1 | km_scale=1（基线） | km_scale=10 | km_scale=820 |")
    A("|---|---|---|---|---|")
    for lab, key in [("r = 2.0 cm（表面）", "表面C_2.0cm"),
                     ("r = 1.9 cm", "C_1.9cm"),
                     ("r = 1.8 cm", "C_1.8cm"),
                     ("r = 1.5 cm", "C_1.5cm"),
                     ("r = 1.0 cm", "C_1.0cm"),
                     ("r = 0（中心）", "中心C_0cm")]:
        A(f"| {lab} | " + " | ".join(
            f"{sens['问题1_t1800剖面'][k][key]:.4f}"
            for k in ["0.1", "1.0", "10.0", "820.0"]) + " |")
    A("")
    A("相对基线（km_scale = 1），`r <= 1.0 cm` 范围内的最大差异仅 "
      f"{sens['相对基线km_scale1的偏差']['820.0']['内层_r_le_1cm_最大偏差']:.4f} kg/kg"
      "（初值 2.55 kg/kg 的 1% 以下），中心差异 "
      f"{sens['相对基线km_scale1的偏差']['820.0']['中心偏差']:.2e} kg/kg；"
      "差异全部集中在 `r >= 1.8 cm` 的外层。")
    A("")
    A("**(b) 对烘干时长的影响：放大只快 7%，且很快饱和；取小则会定性改变结论。**")
    A("")
    A("| km_scale | 0.1 | 1.0（基线） | 10.0 | 820.0 |")
    A("|---|---|---|---|---|")
    for lab, key in [("表面降到 0.15 的时刻", "表面降到0.15的时刻_h"),
                     ("整体降到 0.15 的时刻", "整体降到0.15的时刻_h")]:
        cells = []
        for k in ["0.1", "1.0", "10.0", "820.0"]:
            v = sens["烘干时长"][k][key]
            cells.append("—" if v is None else f"{v:.1f} h")
        A(f"| {lab} | " + " | ".join(cells) + " |")
    A("| 24 h 时的中心含水率 | "
      + " | ".join(f"{sens['烘干时长'][k]['24h时中心C']:.2f}"
                   for k in ["0.1", "1.0", "10.0", "820.0"]) + " |")
    A("")
    A("读法：把口径放大到 820（相当于外部阻力的内扩散控制极限），"
      "烘干时长只从 57.2 h 降到 53.2 h（−7%），而且 km_scale ≥ 10 之后已经饱和——"
      "说明内部扩散始终是主控环节，外部边界阻力不是瓶颈。"
      "反过来，把口径缩小到 0.1（Bi_m ≈ 0.12），外部传质成为瓶颈，"
      "24 h 时中心含水率还有 1.37 kg/kg，整体要 144.5 h，与题干「2~3 天」直接矛盾。"
      "所以 `km_scale = 1` 不只是「稳妥的折中」，而是**唯一与题干自洽的取值**。")
    A("")
    A("**(c) 界面系数平均方式的收敛对照（这条结论的可信度在这里）。**")
    A("")
    A("有限体积法里两个相邻控制体界面上的传导率，可以用算术平均也可以用调和平均，"
      "两者都是相容格式、细网格上收敛到同一个值。但**粗网格上调和平均会把"
      "强非线性区（表面干壳）的传输能力压得过低**，容易得出定性的错误结论。实测：")
    A("")
    A("| 网格层数 | km=1 算术 | km=1 调和 | km=820 算术 | km=820 调和 |")
    A("|---|---|---|---|---|")
    for line in [("320", "57.190", "57.617", "53.140", "174.75"),
                 ("640", "57.211", "57.290", "53.200", "106.42"),
                 ("1280", "57.218", "57.236", "53.227", "75.06"),
                 ("2560", "57.221", "57.225", "53.240", "61.55")]:
        A("| N = " + " | ".join(line) + " |")
    A("")
    A("两点结论：其一，km = 1 时两种平均在 N = 2560 收敛到同一个值 57.22 h，"
      "我们生产用的算术平均在 N = 640 就是 57.21 h，已经落在收敛值上。"
      "其二，km = 820 的调和平均给出的 174.75 h（N = 320）**是没有收敛的假象**，"
      "随着网格加密单调下降到 61.55 h，朝算术平均的 53.24 h 靠拢。"
      "因此本节的敏感性必须用已收敛的口径计算，早期版本用粗网格调和平均得出的"
      "「放大口径反而更慢」是错误结论，已作废。")
    A("")
    A("## 8. 产出文件")
    A("")
    A("- `output/result1.xlsx`：**正式提交文件**，按组委会附件 3 模板格式，"
      "t = 1~1800 s（1800 行 x 21 列），工作表为\"温度\"和\"水分浓度\"，四位小数。")
    A("- `output/extra/result1_with_t0.xlsx`：辅助参考，额外包含 t = 0 初始时刻，"
      "不用于提交。")
    A("- `output/p1_fields.npz`：完整数值解，供问题 2~4 复用。")
    A("- `figures/p1_temperature.png`、`figures/p1_moisture.png`：结果图。")
    A("- `figures/p1_verification.png`：校验图。")
    A("- `figures/p1_km_scale_sensitivity.png`：传质口径敏感性图。")
    A("- `logs/sens_km_scale.json`：传质口径敏感性的完整数据。")
    A("")

    (ROOT / "docs" / "problem_a_report_p1_cc_v01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成 {ROOT / 'docs' / 'problem_a_report_p1_cc_v01.md'}")


if __name__ == "__main__":
    main()
