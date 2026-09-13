# -*- coding: utf-8 -*-
"""生成论文用的图（PDF + PNG）与 LaTeX 表格。

所有数字都从结果文件（output/*.npz、output/tables/*.csv、logs/*.json）读取，
不手抄，避免转录错误。

输出目录：
    paper/figures/*.pdf, *.png
    paper/tables/table*.tex
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
for _sub in ("preprocessing", "models", "analysis", "visualization"):
    sys.path.insert(0, str(ROOT / "src" / _sub))

OUT = ROOT / "outputs" / "submissions" / "problem_a"
LOG = ROOT / "outputs" / "results"
DATA = ROOT / "data" / "processed"
PAPER = ROOT / "paper"
FIG = PAPER / "figures"
TAB = PAPER / "tables"


def setup_plt():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    avail = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]:
        if name in avail:
            matplotlib.rcParams["font.sans-serif"] = [name]
            break
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["font.size"] = 9
    matplotlib.rcParams["figure.dpi"] = 150
    import matplotlib.pyplot as plt
    return plt


def save(fig, name):
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)


# --------------------------------------------------------------- LaTeX 表格
def tex_table(csv_name, caption, label, time_head):
    rows = list(csv.reader((ROOT / "outputs" / "tables" / f"{csv_name}.csv").open(encoding="utf-8-sig")))
    head, body = rows[0], rows[1:]
    cols = [c.replace("cm", "").replace(" ", "") for c in head[1:]]
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{" + caption + "}",
        r"\label{" + label + "}",
        r"\begin{tabular}{c" + "c" * len(cols) + "}",
        r"\toprule",
        time_head + " & " + " & ".join(cols) + r" \\",
        r"\midrule",
    ]
    for r in body:
        t = r[0]
        try:
            tv = f"{float(t):.0f}" if abs(float(t) - round(float(t))) < 1e-9 else f"{float(t):.2f}"
        except ValueError:
            tv = t
        cells = []
        for c in r[1:]:
            if c in ("", "nan"):
                cells.append("--")
            else:
                try:
                    cells.append(f"{float(c):.4f}")
                except ValueError:
                    cells.append(c)
        lines.append(tv + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    text = "\n".join(lines)
    (TAB / f"{label.replace('tab:', 'table')}.tex").write_text(text, encoding="utf-8")
    return text


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    plt = setup_plt()

    p1 = np.load(OUT / "problem_a_result_08_fields_p1_v01.npz")
    p2 = np.load(OUT / "problem_a_result_09_fields_p2_3h_v01.npz")
    p3 = np.load(OUT / "problem_a_result_10_fields_p3_v01.npz")
    p4 = np.load(OUT / "problem_a_result_11_fields_p4_v01.npz")
    ver = json.loads((LOG / "problem_a_result_02_verification_v01.json").read_text(encoding="utf-8"))
    sens = json.loads((LOG / "problem_a_result_05_sensitivity_km_v01.json").read_text(encoding="utf-8"))
    conv = json.loads((LOG / "problem_a_result_03_convergence_face_avg_v01.json").read_text(encoding="utf-8"))
    ext = json.loads((LOG / "problem_a_result_04_convergence_extreme_v01.json").read_text(encoding="utf-8"))
    rad = np.genfromtxt(DATA / "problem_a_processed_radius_v01.csv", delimiter=",", skip_header=1)
    r_cm = 0.1 * np.arange(21)

    # ---------------- 图 1：问题 1 径向剖面 ----------------
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for tt, st in [(100, ":"), (600, "-."), (1200, "--"), (1800, "-")]:
        k = int(np.argmin(np.abs(p1["t"] - tt)))
        ax[0].plot(r_cm, p1["T"][k], st, marker="o", ms=2.5, lw=1.1, label=f"{tt} s")
        ax[1].plot(r_cm, p1["C"][k], st, marker="o", ms=2.5, lw=1.1, label=f"{tt} s")
    ax[0].set_xlabel("到药材中心的距离 / cm"); ax[0].set_ylabel("温度 / ℃")
    ax[1].set_xlabel("到药材中心的距离 / cm"); ax[1].set_ylabel("干基含水率 / (kg/kg)")
    for a in ax:
        a.grid(alpha=0.3); a.legend(fontsize=7)
    save(fig, "fig1_p1_profile")

    # ---------------- 图 2：问题 2 径向剖面 ----------------
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for hh, st in [(0.5, ":"), (1.5, "-."), (3.0, "-")]:
        k = int(np.argmin(np.abs(p2["t"] - hh * 3600)))
        ax[0].plot(r_cm, p2["T"][k], st, marker="o", ms=2.5, lw=1.1, label=f"{hh} h")
        ax[1].plot(r_cm, p2["C"][k], st, marker="o", ms=2.5, lw=1.1, label=f"{hh} h")
    ax[0].set_xlabel("到药材中心的距离 / cm"); ax[0].set_ylabel("温度 / ℃")
    ax[1].set_xlabel("到药材中心的距离 / cm"); ax[1].set_ylabel("干基含水率 / (kg/kg)")
    for a in ax:
        a.grid(alpha=0.3); a.legend(fontsize=7)
    save(fig, "fig2_p2_profile")

    # ---------------- 图 3：问题 3 ----------------
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
    th = p3["t"] / 3600
    ax[0].plot(th, p3["C"][:, 0], lw=1.3, label="中心")
    ax[0].plot(th, p3["C"][:, -1], lw=1.3, label="表面")
    ax[0].axhline(0.15, color="r", ls=":", lw=1)
    ax[0].annotate(f"{p3['t'][-1] / 3600:.2f} h", xy=(p3["t"][-1] / 3600, 0.15),
                   xytext=(-46, 16), textcoords="offset points", fontsize=8,
                   arrowprops=dict(arrowstyle="->", lw=0.8))
    ax[0].set_xlabel("时间 / h"); ax[0].set_ylabel("干基含水率 / (kg/kg)")
    ax[0].grid(alpha=0.3); ax[0].legend(fontsize=7)
    for hh in [6, 18, 36, 54]:
        k = int(np.argmin(np.abs(p3["t"] - hh * 3600)))
        ax[1].plot(r_cm, p3["C"][k], marker="o", ms=2.5, lw=1.1, label=f"{hh} h")
    ax[1].plot(r_cm, p3["C"][-1], "k-", lw=1.6,
               label=f"{p3['t'][-1] / 3600:.2f} h")
    ax[1].axhline(0.15, color="r", ls=":", lw=1)
    ax[1].set_xlabel("到药材中心的距离 / cm"); ax[1].set_ylabel("干基含水率 / (kg/kg)")
    ax[1].grid(alpha=0.3); ax[1].legend(fontsize=7)
    save(fig, "fig3_p3")

    # ---------------- 图 4：问题 4 ----------------
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
    ax[0].plot(rad[:, 0] / 3600, rad[:, 1], "o", ms=2.5, mfc="none", label="附件 2 实测")
    ax[0].plot(p4["t"] / 3600, p4["R"] * 100, "-", lw=1.2, label="插值 R(t)")
    ax[0].set_xlabel("时间 / h"); ax[0].set_ylabel("半径 / cm")
    ax[0].grid(alpha=0.3); ax[0].legend(fontsize=7)
    ax[1].plot(p4["t"] / 3600, p4["C"][:, 0], lw=1.3, label="中心")
    ax[1].plot(p4["t"] / 3600, p4["C"][:, -1], lw=1.3, label="表面")
    ax[1].axhline(0.15, color="r", ls=":", lw=1)
    ax[1].annotate(f"{p4['t'][-1] / 3600:.2f} h", xy=(p4["t"][-1] / 3600, 0.15),
                   xytext=(-46, 16), textcoords="offset points", fontsize=8,
                   arrowprops=dict(arrowstyle="->", lw=0.8))
    ax[1].set_xlabel("时间 / h"); ax[1].set_ylabel("干基含水率 / (kg/kg)")
    ax[1].grid(alpha=0.3); ax[1].legend(fontsize=7)
    save(fig, "fig4_p4")

    # ---------------- 图 5：模型检验 ----------------
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 2.8))
    lv = [f"({c['coarse'][0]},{c['coarse'][1]})→({c['fine'][0]},{c['fine'][1]})"
          for c in ver["收敛性"]["逐级差"]]
    eT = [c["dT"] for c in ver["收敛性"]["逐级差"]]
    eC = [c["dC"] for c in ver["收敛性"]["逐级差"]]
    x = np.arange(len(eT))
    ax[0].semilogy(x, eT, "o-", ms=3, lw=1.1, label="温度 / K")
    ax[0].semilogy(x, eC, "s-", ms=3, lw=1.1, label="含水率 / (kg/kg)")
    ax[0].set_xticks(x); ax[0].set_xticklabels(lv, fontsize=5.5, rotation=30)
    ax[0].set_ylabel("相邻网格解的最大偏差")
    ax[0].set_title("(a) 网格与时间步收敛", fontsize=8.5)
    ax[0].grid(alpha=0.3, which="both"); ax[0].legend(fontsize=6.5)

    tl = sens["烘干时长"]
    ks = ["0.1", "1.0", "10.0", "820.0"]
    vals = [tl[k]["整体降到0.15的时刻_h"] for k in ks]
    ax[1].plot(range(len(ks)), vals, "o-", ms=4, lw=1.2, color="tab:red")
    for i, v in enumerate(vals):
        ax[1].annotate(f"{v:.1f}", (i, v), textcoords="offset points",
                       xytext=(0, 6), ha="center", fontsize=7)
    ax[1].set_xticks(range(len(ks)))
    ax[1].set_xticklabels(["0.1", "1（基线）", "10", "820"], fontsize=7)
    ax[1].set_xlabel("km_scale"); ax[1].set_ylabel("烘干时长 / h")
    ax[1].set_title("(b) 传质口径灵敏度", fontsize=8.5)
    ax[1].grid(alpha=0.3)

    for key, st, mk in [("km1.0_arithmetic", "-", "o"), ("km1.0_harmonic", "--", "s"),
                        ("km820.0_arithmetic", "-.", "^"),
                        ("km820.0_harmonic", ":", "v")]:
        d = {}
        for src in (conv, ext):
            for k, v in src.items():
                if k.startswith(key + "_N"):
                    d[int(k.split("_N")[1])] = v
        if not d:
            continue
        ns = sorted(d)
        lab = key.replace("km1.0", "km=1").replace("km820.0", "km=820") \
                 .replace("_arithmetic", " 算术").replace("_harmonic", " 调和")
        ax[2].semilogy(ns, [d[n] for n in ns], st, marker=mk, ms=3, lw=1.1, label=lab)
    ax[2].set_xlabel("径向单元数 N"); ax[2].set_ylabel("烘干时长 / h")
    ax[2].set_title("(c) 界面平均方式的收敛对照", fontsize=8.5)
    ax[2].grid(alpha=0.3, which="both"); ax[2].legend(fontsize=6.5)
    save(fig, "fig5_verification")

    # ---------------- LaTeX 表格 ----------------
    tex_table("problem_a_table_01_p1_temperature_v01", "问题 1：预热阶段药材温度（单位：$^\\circ$C）", "table_01_p1_temperature", "时间 / s")
    tex_table("problem_a_table_02_p1_moisture_v01", "问题 1：预热阶段药材干基含水率（单位：kg/kg）", "table_02_p1_moisture", "时间 / s")
    tex_table("problem_a_table_03_p2_temperature_v01", "问题 2：3 h 内药材温度（单位：$^\\circ$C）", "table_03_p2_temperature", "时间 / h")
    tex_table("problem_a_table_04_p2_moisture_v01", "问题 2：3 h 内药材干基含水率（单位：kg/kg）", "table_04_p2_moisture", "时间 / h")
    tex_table("problem_a_table_05_p3_moisture_v01", "问题 3：固定半径下各时刻的干基含水率（单位：kg/kg）", "table_05_p3_moisture", "时间 / h")
    tex_table("problem_a_table_06_p4_moisture_v01", "问题 4：考虑收缩时各时刻的干基含水率（单位：kg/kg）", "table_06_p4_moisture", "时间 / h")
    print("图与表已生成：", FIG, TAB)


if __name__ == "__main__":
    main()
