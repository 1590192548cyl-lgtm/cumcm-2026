# -*- coding: utf-8 -*-
"""问题 1：预热平衡阶段药材温度与水分浓度的数值求解与结果输出。

运行：  python src/run_p1.py
产物：  output/result1.xlsx            按附件 3 模板（t = 1..1800 s）
        output/result1_with_t0.xlsx   含初始时刻 t = 0 的完整版本
        output/tables/*.csv          论文表 1、表 2
        output/p1_fields.npz         完整数值解（供问题 2~4 复用）
        figures/*.png                结果图
"""

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
for _sub in ("preprocessing", "models", "analysis", "visualization"):
    sys.path.insert(0, str(ROOT / "src" / _sub))

import problem_a_02_config_cc_v01 as cfg                                     # noqa: E402
from problem_a_04_fv_solver_cc_v01 import CylinderFV                                # noqa: E402
from problem_a_01_preprocess_cc_v01 import run_preprocess, load_ambient      # noqa: E402

OUT = ROOT / "outputs" / "submissions" / "problem_a"
FIG = ROOT / "outputs" / "figures"
LOG = ROOT / "outputs" / "results"


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    avail = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC"]:
        if name in avail:
            matplotlib.rcParams["font.sans-serif"] = [name]
            break
    matplotlib.rcParams["axes.unicode_minus"] = False
    import matplotlib.pyplot as plt
    return plt


class AmbientConst:
    """恒定环境边界条件（用于解析解校验）。"""

    def __init__(self, T, C):
        self.Tv = float(T)
        self.Cv = float(C)

    def T_air(self, t):
        return self.Tv

    def C_air(self, t):
        return self.Cv


def solve(steps=None, dt=None, n_cells=None, ambient=None,
          km_scale=1.0, props=None, D_fun=None):
    """跑一次正演，返回时间序列与历史场。

    计算网格是 n_cells 个单元，记录时按 n_cells / N_OUT 抽样，
    使历史场的列正好对应题目要求的 0、0.1、…、2.0 cm。
    内部积分步长 cfg.DT = 0.1 s，记录间隔 cfg.DT_OUT = 1 s。
    """
    dt = cfg.DT if dt is None else float(dt)
    n_rec = int(round(cfg.T_END / cfg.DT_OUT)) if steps is None else int(steps)
    n_sub = int(round(cfg.DT_OUT / dt))
    n_cells = cfg.N_CELLS if n_cells is None else int(n_cells)
    amb = load_ambient() if ambient is None else ambient
    props = cfg.props_const if props is None else props
    D_fun = cfg.D_fun_p1 if D_fun is None else D_fun
    stride = n_cells // cfg.N_OUT
    idx = np.arange(0, n_cells + 1, stride)
    n_out = idx.size

    model = CylinderFV(R=cfg.R0, n_cells=n_cells, h=cfg.H_CONV, km=cfg.KM_CONV,
                       T0=cfg.T_INIT, C0=cfg.C_INIT,
                       props=props, D_fun=D_fun, km_scale=km_scale)

    t_hist = np.zeros(n_rec + 1)
    T_hist = np.zeros((n_rec + 1, n_out))
    C_hist = np.zeros((n_rec + 1, n_out))
    T_air_hist = np.zeros(n_rec + 1)
    C_air_hist = np.zeros(n_rec + 1)
    T_hist[0] = model.T[idx]
    C_hist[0] = model.C[idx]
    T_air_hist[0] = amb.T_air(0.0)
    C_air_hist[0] = amb.C_air(0.0)

    t0 = time.time()
    for k in range(1, n_rec + 1):
        for j in range(1, n_sub + 1):
            tk = ((k - 1) * n_sub + j) * dt
            model.step(dt, amb.T_air(tk), amb.C_air(tk))
        t_hist[k] = k * cfg.DT_OUT
        T_hist[k] = model.T[idx]
        C_hist[k] = model.C[idx]
        T_air_hist[k] = model.last_T_air
        C_air_hist[k] = model.last_C_air
    wall = time.time() - t0
    return dict(model=model, t=t_hist, T=T_hist, C=C_hist,
                T_air=T_air_hist, C_air=C_air_hist, wall=wall, dt=dt)


def write_result1(res, path, include_t0=False):
    import openpyxl
    from openpyxl.styles import Alignment, Font

    t = res["t"]
    if not include_t0:
        t = t[1:]
        T = res["T"][1:]
        C = res["C"][1:]
    else:
        T = res["T"]
        C = res["C"]

    n_r = T.shape[1]
    header_r = [round(0.1 * j, 1) for j in range(n_r)]

    wb = openpyxl.Workbook()
    for k, (sheet, data) in enumerate([("温度", T), ("水分浓度", C)]):
        ws = wb.active if k == 0 else wb.create_sheet()
        ws.title = sheet
        ws.cell(row=1, column=1, value="时间\\到药材中心的距离").font = Font(bold=True)
        for j, val in enumerate(header_r):
            c = ws.cell(row=1, column=2 + j, value=float(val))
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="center")
        for i in range(len(t)):
            ws.cell(row=2 + i, column=1, value=int(round(t[i])))
            for j in range(n_r):
                ws.cell(row=2 + i, column=2 + j, value=float(round(data[i, j], 4)))
        ws.column_dimensions["A"].width = 20
        ws.freeze_panes = "B2"
    wb.save(path)


def write_tables(res):
    import csv
    table_dir = ROOT / "outputs" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    r_idx = [int(round(v / 0.1)) for v in cfg.R_TABLE_CM]
    t = res["t"]

    def dump(name, data, unit):
        rows = []
        for tt in cfg.T_TABLE:
            k = int(np.argmin(np.abs(t - tt)))
            rows.append([tt] + [round(float(data[k, j]), 4) for j in r_idx])
        with open(table_dir / f"{name}.csv", "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["时间/s"] + [f"{v}cm" for v in cfg.R_TABLE_CM])
            w.writerows(rows)
        lines = [f"| 时间/s | " + " | ".join(f"{v} cm" for v in cfg.R_TABLE_CM) + " |",
                 "|" + "---|" * (len(cfg.R_TABLE_CM) + 1)]
        for r in rows:
            lines.append("| " + " | ".join(f"{v:.4f}" for v in r) + " |")
        (table_dir / f"{name}.md").write_text(
            f"# {name}（单位：{unit}）\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
        return rows

    t1 = dump("problem_a_table_01_p1_temperature_v01", res["T"], "摄氏度")
    t2 = dump("problem_a_table_02_p1_moisture_v01", res["C"], "kg/kg")
    return t1, t2


def make_figures(res):
    plt = setup_matplotlib()
    t = res["t"]
    r_cm = 0.1 * np.arange(res["T"].shape[1])
    picks = [0, 2, 5, 10, 15, 20]

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(t / 60, res["T_air"], "k--", lw=1, label="烘房空气 T_a")
    for j in picks:
        ax[0].plot(t / 60, res["T"][:, j], lw=1.3, label=f"r = {r_cm[j]:.1f} cm")
    ax[0].set_xlabel("时间 / min")
    ax[0].set_ylabel("温度 / 摄氏度")
    ax[0].set_title("药材温度随时间变化（问题 1）")
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=0.3)
    for tt, style in [(600, ":"), (1800, "-")]:
        k = int(np.argmin(np.abs(t - tt)))
        ax[1].plot(r_cm, res["T"][k], style, marker="o", ms=3, label=f"t = {int(t[k])} s")
    ax[1].set_xlabel("到药材中心的距离 / cm")
    ax[1].set_ylabel("温度 / 摄氏度")
    ax[1].set_title("温度沿半径的分布")
    ax[1].legend()
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "problem_a_figure_07_p1_temperature_v01.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(t / 60, res["C_air"], "k--", lw=1, label="烘房空气 C_a")
    for j in picks:
        ax[0].plot(t / 60, res["C"][:, j], lw=1.3, label=f"r = {r_cm[j]:.1f} cm")
    ax[0].set_xlabel("时间 / min")
    ax[0].set_ylabel("水分浓度 / (kg/kg)")
    ax[0].set_title("药材水分浓度随时间变化（问题 1）")
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=0.3)
    for tt, style in [(600, ":"), (1800, "-")]:
        k = int(np.argmin(np.abs(t - tt)))
        ax[1].plot(r_cm, res["C"][k], style, marker="o", ms=3, label=f"t = {int(t[k])} s")
    ax[1].set_xlabel("到药材中心的距离 / cm")
    ax[1].set_ylabel("水分浓度 / (kg/kg)")
    ax[1].set_title("水分浓度沿半径的分布")
    ax[1].legend()
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "problem_a_figure_08_p1_moisture_v01.png", dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    LOG.mkdir(exist_ok=True)

    print("=" * 72)
    print("步骤 1  数据预处理")
    print("=" * 72)
    run_preprocess()

    print()
    print("=" * 72)
    print("步骤 2  数值求解（全隐式有限体积，dr = 0.1 cm，dt = 1 s）")
    print("=" * 72)
    res = solve()
    print(f"  完成 {int(res['t'][-1])} 步，用时 {res['wall']:.2f} s，"
          f"平均 Picard 迭代 {np.mean(res['model'].n_iters):.2f} 次/步，"
          f"最大 {max(res['model'].n_iters)} 次")

    print()
    print("=" * 72)
    print("步骤 3  输出结果文件")
    print("=" * 72)
    p1 = OUT / "result1.xlsx"
    write_result1(res, p1, include_t0=False)
    (OUT / "extra").mkdir(exist_ok=True)
    p1b = OUT / "extra" / "result1_with_t0.xlsx"
    write_result1(res, p1b, include_t0=True)
    print(f"  {p1}  （{res['T'].shape[0] - 1} 行 x {res['T'].shape[1]} 列，模板格式）")
    print(f"  {p1b}  （辅助参考，含 t = 0，不用于提交）")

    t1, t2 = write_tables(res)
    np.savez_compressed(OUT / "problem_a_result_08_fields_p1_v01.npz", t=res["t"], r=0.1 * np.arange(res["T"].shape[1]),
                        T=res["T"], C=res["C"], T_air=res["T_air"], C_air=res["C_air"])
    print(f"  {OUT / 'tables'}  表 1、表 2")
    print(f"  {OUT / 'p1_fields.npz'}")

    make_figures(res)
    print(f"  {FIG / 'p1_temperature.png'} , {FIG / 'p1_moisture.png'}")

    # ---------------- 诊断与守恒校验 ----------------
    e_res, m_res = res["model"].check_balances()
    diag = {
        "网格": {"N_cells": cfg.N_CELLS, "dr_cm": 0.1, "dt_s": cfg.DT},
        "无量纲数": {
            "长径比 L/R": cfg.LENGTH / cfg.R0,
            "热_Biot_hR_k": cfg.H_CONV * cfg.R0 / cfg.K_COND,
            "传质_Biot_kmR_D": cfg.KM_CONV * cfg.R0 / float(cfg.D_of_C(cfg.C_INIT)),
            "热扩散率_alpha_m2s": cfg.K_COND / (cfg.RHO * cfg.CP),
            "Luikov_D_alpha": float(cfg.D_of_C(cfg.C_INIT)) / (cfg.K_COND / (cfg.RHO * cfg.CP)),
            "Fo_热_t1800": (cfg.K_COND / (cfg.RHO * cfg.CP)) * 1800.0 / cfg.R0 ** 2,
            "Fo_质_t1800": float(cfg.D_of_C(cfg.C_INIT)) * 1800.0 / cfg.R0 ** 2,
        },
        "守恒残差": {"能量相对残差": e_res, "水分相对残差": m_res},
        "t=1800s": {
            "中心温度": float(res["T"][-1, 0]),
            "表面温度": float(res["T"][-1, -1]),
            "中心水分浓度": float(res["C"][-1, 0]),
            "表面水分浓度": float(res["C"][-1, -1]),
        },
    }
    (LOG / "problem_a_result_01_diagnostics_v01.json").write_text(
        json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 72)
    print("步骤 4  物理诊断")
    print("=" * 72)
    print(f"  热 Biot 数 hR/k = {diag['无量纲数']['热_Biot_hR_k']:.4f}"
          f"（> 0.1，集总参数法不适用）")
    print(f"  传质 Biot 数 kmR/D = {diag['无量纲数']['传质_Biot_kmR_D']:.4f}")
    print(f"  Luikov 数 D/alpha = {diag['无量纲数']['Luikov_D_alpha']:.4f}"
          f"（热扩散比水分扩散快 {1 / diag['无量纲数']['Luikov_D_alpha']:.0f} 倍）")
    print(f"  1800 s 时 Fo_热 = {diag['无量纲数']['Fo_热_t1800']:.4f}，"
          f"Fo_质 = {diag['无量纲数']['Fo_质_t1800']:.4f}")
    print(f"  守恒残差：能量 {e_res:.3e}，水分 {m_res:.3e}")
    print(f"  t=1800 s：中心温度 {diag['t=1800s']['中心温度']:.4f}，"
          f"表面温度 {diag['t=1800s']['表面温度']:.4f}")
    print(f"  t=1800 s：中心水分浓度 {diag['t=1800s']['中心水分浓度']:.4f}，"
          f"表面水分浓度 {diag['t=1800s']['表面水分浓度']:.4f}")
    print()
    print("表 1  30 分钟内药材的温度（摄氏度）")
    for row in t1:
        print("   " + "  ".join(f"{v:.4f}" for v in row))
    print("表 2  30 分钟内药材的水分浓度（kg/kg）")
    for row in t2:
        print("   " + "  ".join(f"{v:.4f}" for v in row))


if __name__ == "__main__":
    main()
