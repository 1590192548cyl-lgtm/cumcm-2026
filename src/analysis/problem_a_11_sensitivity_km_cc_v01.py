# -*- coding: utf-8 -*-
"""对流传质边界条件口径 km_scale 的定量敏感性分析。

回答两个问题：
  (1) 对问题 1 的结果表（0~1800 s）影响多大？分部位看：表面列 / 中间列 / 中心列
  (2) 对烘干总时长（问题 3 的判据 max_r C <= 0.15）影响多大？

同时给出传质 Biot 数随含水率的变化，从机理上说明为什么影响会先大后小。

注意：问题 3 用附录 3 的物性公式，因此长时程部分改用附录 3 的
rho(C)、cp(C)、k(C)、D(C,T) 计算，边界条件按附件 1 插值（4 h 后自动取平台值）。
"""

import json
import sys
from pathlib import Path

import numpy as np

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
for _sub in ("preprocessing", "models", "analysis", "visualization"):
    sys.path.insert(0, str(ROOT / "src" / _sub))

import problem_a_02_config_cc_v01 as cfg                                     # noqa: E402
from problem_a_04_fv_solver_cc_v01 import CylinderFV                                # noqa: E402
from problem_a_01_preprocess_cc_v01 import load_ambient                      # noqa: E402

OUT = ROOT / "outputs" / "submissions" / "problem_a"
LOG = ROOT / "outputs" / "results"
FIG = ROOT / "outputs" / "figures"

KM_LIST = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0, 820.0]
KM_LONG = [0.1, 1.0, 10.0, 820.0]

# 敏感性分析与生产口径保持一致：640 个径向单元 + 算术平均。
# 界面平均方式已经单独做过收敛对照（见 src/convergence_face_avg.py 与
# src/convergence_extreme.py）：算术与调和在细网格上收敛到同一个值，
# 640 单元的算术平均已经落在收敛值上（差 0.02%），而调和平均在同等网格上还有 0.12% 偏差。
SENS_N = 640


def props3(T, C):
    """附录 3：rho、cp、k 均为含水率 C 的函数。"""
    C = np.asarray(C, dtype=float)
    rho = 650.0 + 128.0 * C
    cp = 1450.0 + 2736.0 * C / (C + 1.0)
    k = 0.21 + 0.38 * C / (C + 1.0)
    return rho, cp, k


def D3(C, T):
    """附录 3：D = 2.4e-3 * exp(-0.45/C) * exp(-3850/T)，T 取开尔文。"""
    C = np.maximum(np.asarray(C, dtype=float), cfg.C_FLOOR)
    Tk = np.asarray(T, dtype=float) + 273.15
    return 2.4e-3 * np.exp(-0.45 / C) * np.exp(-3850.0 / Tk)


def run(n_cells, dt, steps, km_scale, props, D_fun, amb):
    model = CylinderFV(R=cfg.R0, n_cells=n_cells, h=cfg.H_CONV, km=cfg.KM_CONV,
                       T0=cfg.T_INIT, C0=cfg.C_INIT, props=props, D_fun=D_fun,
                       km_scale=km_scale, relax=0.7, max_iter=60, tol=1e-10,
                       face_avg="arithmetic")
    for k in range(1, steps + 1):
        model.step(dt, amb.T_air(k * dt), amb.C_air(k * dt))
    return model


def main():
    amb = load_ambient()
    out = {}
    r_cm = 0.1 * np.arange(21)

    print("=" * 78)
    print("传质 Biot 数 Bi_m = km*R/D（附录 3 物性，T = 50 摄氏度）")
    print("=" * 78)
    bi_table = {}
    for c in [2.55, 2.0, 1.5, 1.0, 0.5, 0.3, 0.15]:
        Dv = float(D3(np.array([c]), np.array([50.0]))[0])
        bim = cfg.KM_CONV * cfg.R0 / Dv
        bi_table[str(c)] = {"D": Dv, "Bi_m": bim}
        print(f"  C = {c:5.2f} kg/kg : D = {Dv:.3e} m^2/s, Bi_m = {bim:8.2f}")
    out["传质Biot数"] = bi_table
    print("  说明：C 降低时 D 塌缩，Bi_m 由 1.2 增大到 20，内部扩散全程是主控环节。")
    print("        因此外边界阻力的影响有限，见第 (2) 部分的定量结果。")

    print()
    print("=" * 78)
    print("(1) 对问题 1 结果的影响（t = 1800 s，附录 2 物性）")
    print("=" * 78)
    q1 = {}
    profiles = {}
    sel = np.arange(0, SENS_N + 1, SENS_N // cfg.N_OUT)   # 0.1 cm 输出点
    for ks in KM_LIST:
        model = run(SENS_N, 1.0, 1800, ks, cfg.props_const, cfg.D_fun_p1, amb)
        C = model.C[sel]
        profiles[ks] = C.copy()
        hit = np.where(np.abs(C - cfg.C_INIT) > 0.005)[0]
        depth = float((cfg.N_OUT - hit.min()) * 0.1) if hit.size else 0.0
        q1[str(ks)] = {
            "表面C_2.0cm": float(C[-1]),
            "C_1.9cm": float(C[-2]),
            "C_1.8cm": float(C[-3]),
            "C_1.5cm": float(C[5]),
            "C_1.0cm": float(C[10]),
            "中心C_0cm": float(C[0]),
            "平均C": float(np.sum(model.a * model.C) / np.sum(model.a)),
            "受影响层厚_cm": depth,
        }
        print(f"  km_scale={ks:7.1f} : 表面 {C[-1]:.4f} | 1.9cm {C[-2]:.4f} | "
              f"1.8cm {C[-3]:.4f} | 1.5cm {C[5]:.4f} | 1.0cm {C[10]:.4f} | "
              f"中心 {C[0]:.4f} | 均值 {q1[str(ks)]['平均C']:.4f}")

    ref = profiles[1.0]
    print()
    dev = {}
    for ks in KM_LIST:
        d = np.abs(profiles[ks] - ref)
        dev[str(ks)] = {
            "最大偏差_kgkg": float(d.max()),
            "所在半径_cm": float(0.1 * int(np.argmax(d))),
            "内层_r_le_1cm_最大偏差": float(d[:11].max()),
            "中心偏差": float(d[0]),
        }
        print(f"  相对基线 km_scale=1：全剖面 max 偏差 {d.max():.4f} kg/kg "
              f"(r={0.1 * int(np.argmax(d)):.1f} cm)，r<=1.0cm 内 {d[:11].max():.5f}，"
              f"中心 {d[0]:.2e}")
    out["问题1_t1800剖面"] = q1
    out["相对基线km_scale1的偏差"] = dev

    print()
    print("=" * 78)
    print("(2) 对烘干总时长的影响（附录 3 物性，判据 max_r C <= 0.15）")
    print("=" * 78)
    dt_long = 60.0
    steps_long = int(15 * 24 * 3600 / dt_long)
    long_res = {}
    for ks in KM_LONG:
        model = CylinderFV(R=cfg.R0, n_cells=SENS_N, h=cfg.H_CONV, km=cfg.KM_CONV,
                           T0=cfg.T_INIT, C0=cfg.C_INIT, props=props3, D_fun=D3,
                           km_scale=ks, relax=0.7, max_iter=60, tol=1e-10,
                           face_avg="arithmetic")
        t_surface = None
        t_reach = None
        snap24 = None
        for k in range(1, steps_long + 1):
            tk = k * dt_long
            model.step(dt_long, amb.T_air(tk), amb.C_air(tk))
            if t_surface is None and model.C[-1] <= 0.15:
                t_surface = model.t
            if snap24 is None and model.t >= 24 * 3600:
                snap24 = model.C.copy()
            if model.C.max() <= 0.15:
                t_reach = model.t
                break
        long_res[str(ks)] = {
            "表面降到0.15的时刻_h": None if t_surface is None else t_surface / 3600.0,
            "整体降到0.15的时刻_h": None if t_reach is None else t_reach / 3600.0,
            "24h时中心C": None if snap24 is None else float(snap24[0]),
            "24h时表面C": None if snap24 is None else float(snap24[-1]),
        }
        tag = "3.5 天内未达到" if t_reach is None else f"{t_reach / 3600.0:.2f} h"
        print(f"  km_scale={ks:7.1f} : 表面达标 "
              f"{'--' if t_surface is None else f'{t_surface / 3600.0:6.2f} h'}，"
              f"整体达标 {tag}，24 h 时中心 "
              f"{long_res[str(ks)]['24h时中心C']:.4f} / 表面 "
              f"{long_res[str(ks)]['24h时表面C']:.4f}")
    out["烘干时长"] = long_res

    base = long_res["1.0"]["整体降到0.15的时刻_h"]
    if base:
        rel = {}
        print()
        for ks in KM_LONG:
            v = long_res[str(ks)]["整体降到0.15的时刻_h"]
            if v:
                rel[str(ks)] = (v - base) / base * 100.0
                print(f"  km_scale={ks:7.1f} : {v:.2f} h，相对基线 {v - base:+.2f} h "
                      f"({(v - base) / base * 100:+.1f}%)")
        out["烘干时长相对偏差_pct"] = rel

    print()
    print("=" * 78)
    print("长时程时间步长无关性检查（km_scale = 1）")
    print("=" * 78)
    chk = {}
    for dt_c in [60.0, 15.0]:
        model = CylinderFV(R=cfg.R0, n_cells=SENS_N, h=cfg.H_CONV, km=cfg.KM_CONV,
                           T0=cfg.T_INIT, C0=cfg.C_INIT, props=props3, D_fun=D3,
                           km_scale=1.0, relax=0.7, max_iter=60, tol=1e-10,
                           face_avg="arithmetic")
        t_reach = None
        for k in range(1, int(3.5 * 24 * 3600 / dt_c) + 1):
            model.step(dt_c, amb.T_air(k * dt_c), amb.C_air(k * dt_c))
            if model.C.max() <= 0.15:
                t_reach = model.t
                break
        chk[str(dt_c)] = None if t_reach is None else t_reach / 3600.0
        txt = "未达到" if t_reach is None else f"{t_reach / 3600.0:.3f} h"
        print(f"  dt = {dt_c:5.1f} s : 整体达标 {txt}")
    out["长时程时间步检查"] = chk

    (LOG / "problem_a_result_05_sensitivity_km_v01.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager
    avail = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Microsoft YaHei", "SimHei"]:
        if name in avail:
            matplotlib.rcParams["font.sans-serif"] = [name]
            break
    matplotlib.rcParams["axes.unicode_minus"] = False
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3))
    for ks in KM_LIST:
        ax[0].plot(r_cm, profiles[ks], marker="o", ms=3, lw=1.2, label=f"km_scale={ks:g}")
    ax[0].set_xlabel("到药材中心的距离 / cm")
    ax[0].set_ylabel("水分浓度 / (kg/kg)")
    ax[0].set_title("问题 1：t = 1800 s 的水分浓度剖面")
    ax[0].legend(fontsize=7)
    ax[0].grid(alpha=0.3)

    cs = [float(c) for c in bi_table.keys()]
    bm = [bi_table[c]["Bi_m"] for c in bi_table.keys()]
    ax[1].loglog(cs, bm, "o-")
    ax[1].axhline(1.0, color="k", ls=":", lw=1)
    ax[1].set_xlabel("水分浓度 C / (kg/kg)")
    ax[1].set_ylabel("传质 Biot 数  km*R/D")
    ax[1].set_title("传质 Biot 数随含水率的变化")
    ax[1].grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(FIG / "p1_km_scale_sensitivity.png", dpi=160)
    plt.close(fig)
    print()
    print(f"结果：{LOG / 'sens_km_scale.json'}")
    print(f"图：  {FIG / 'p1_km_scale_sensitivity.png'}")


if __name__ == "__main__":
    main()
