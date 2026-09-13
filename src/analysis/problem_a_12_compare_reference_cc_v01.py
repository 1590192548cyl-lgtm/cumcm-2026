# -*- coding: utf-8 -*-
"""与同学论文（problem_a_paper_cc_v01.pdf）的结果逐项比对。

比对分三层：
  1. 数值本身差多少（问题 1、2 的表格逐点比）
  2. 差异是不是网格分辨率造成的（我们自己加密重算）
  3. 差异是不是界面系数平均方式造成的（算术平均 vs 调和平均）
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
from problem_a_03_properties_cc_v01 import props3, D3, props4, D4, RadiusCurve    # noqa: E402

LOG = ROOT / "outputs" / "results"

# ---- 同学论文中的数值（手工摘录自 PDF）----
CC_P1 = {   # t: (T_center, T_surface, C_center, C_surface)
    100: (28.0001, 28.1801, 2.5500, 2.2470),
    300: (28.0408, 28.8488, 2.5500, 2.0508),
    600: (28.4533, 30.1652, 2.5500, 1.8770),
    900: (29.3243, 31.7304, 2.5500, 1.7547),
    1200: (30.5427, 33.4276, 2.5500, 1.6586),
    1500: (31.9957, 35.1203, 2.5500, 1.5787),
    1800: (33.5753, 36.7856, 2.5500, 1.5102),
}
CC_P2 = {   # 小时: (T_center, T_surface, C_center, C_surface)
    0.5: (32.1893, 35.4131, 2.5499, 1.6486),
    1.0: (40.3816, 42.9976, 2.5257, 1.4711),
    1.5: (45.8468, 47.1400, 2.3861, 1.3476),
    2.0: (48.4503, 49.0034, 2.1709, 1.2311),
    2.5: (49.4670, 49.6609, 1.9566, 1.1166),
    3.0: (49.8495, 49.9664, 1.7662, 1.0081),
}
CC_TIME = {"P3_h": 57.1724, "P4_h": 50.8246, "P4_eta_percent": 11.10}


def run_p1(amb, n_cells, face_avg="arithmetic", dt=1.0, steps=1800):
    m = CylinderFV(R=cfg.R0, n_cells=n_cells, h=cfg.H_CONV, km=cfg.KM_CONV,
                   T0=cfg.T_INIT, C0=cfg.C_INIT, props=cfg.props_const,
                   D_fun=cfg.D_fun_p1, face_avg=face_avg)
    rec = {}
    for k in range(1, steps + 1):
        m.step(dt, amb.T_air(k * dt), amb.C_air(k * dt))
        if abs(k * dt - round(k * dt)) < 1e-9 and int(round(k * dt)) in CC_P1:
            rec[int(round(k * dt))] = (m.T[0], m.T[-1], m.C[0], m.C[-1])
    return rec


def run_p2(amb, n_cells, face_avg="arithmetic", dt=1.0):
    m = CylinderFV(R=cfg.R0, n_cells=n_cells, h=cfg.H_CONV, km=cfg.KM_CONV,
                   T0=cfg.T_INIT, C0=cfg.C_INIT, props=props3, D_fun=D3,
                   face_avg=face_avg)
    rec = {}
    targets = {int(h * 3600) for h in CC_P2}
    for k in range(1, 10801):
        m.step(dt, amb.T_air(k * dt), amb.C_air(k * dt))
        if k in targets:
            rec[k / 3600.0] = (m.T[0], m.T[-1], m.C[0], m.C[-1])
    return rec


def drying_time(props, D_fun, amb, n_cells=20, face_avg="arithmetic",
                dt=60.0, R_fun=None, t_max=20 * 24 * 3600.0, km_scale=1.0):
    m = CylinderFV(R=cfg.R0, n_cells=n_cells, h=cfg.H_CONV, km=cfg.KM_CONV,
                   T0=cfg.T_INIT, C0=cfg.C_INIT, props=props, D_fun=D_fun,
                   km_scale=km_scale, relax=0.7, max_iter=80, tol=1e-10,
                   R_fun=R_fun, face_avg=face_avg)
    if R_fun is not None:
        m.R = float(R_fun(0.0))
    t = 0.0
    C_prev = float(m.C.max())
    while t < t_max:
        step = 1.0 if t < 3600.0 else dt
        t_new = t + step
        R_new = None if R_fun is None else float(R_fun(t_new))
        m.step(step, amb.T_air(t_new), amb.C_air(t_new), R=R_new)
        C_now = float(m.C.max())
        if C_now <= 0.15:
            # 与同学论文一致：在跨越阈值的两个时间层之间线性插值
            f = (C_prev - 0.15) / (C_prev - C_now)
            return (t + f * step) / 3600.0
        C_prev = C_now
        t = t_new
    return None


def main():
    amb = load_ambient()
    out = {}

    # ---------------- 问题 1 ----------------
    print("=" * 92)
    print("问题 1 逐点比对（同学论文表 2 / 我们的表 1、2）")
    print("=" * 92)
    ours20 = run_p1(amb, 20)
    ours640 = run_p1(amb, 640)
    print(f"{'t/s':>6} {'量':>4} | {'同学':>10} {'我们N=20':>10} {'差':>9} | "
          f"{'我们N=640':>10} {'差':>9}")
    p1_rows = []
    for t in sorted(CC_P1):
        cc = CC_P1[t]
        for j, (name, unit) in enumerate([("T中心", "C"), ("T表面", "C"),
                                          ("C中心", ""), ("C表面", "")]):
            d20 = ours20[t][j] - cc[j]
            d640 = ours640[t][j] - cc[j]
            p1_rows.append((t, name, cc[j], ours20[t][j], d20, ours640[t][j], d640))
            print(f"{t:>6} {name:>4} | {cc[j]:>10.4f} {ours20[t][j]:>10.4f} "
                  f"{d20:>+9.4f} | {ours640[t][j]:>10.4f} {d640:>+9.4f}")
    out["问题1"] = [{"t": r[0], "量": r[1], "同学": r[2], "我们N20": r[3],
                     "差N20": r[4], "我们N640": r[5], "差N640": r[6]}
                    for r in p1_rows]
    e20 = max(abs(r[4]) for r in p1_rows)
    e640 = max(abs(r[6]) for r in p1_rows)
    print(f"\n最大绝对偏差：N=20 时 {e20:.4f}；N=640 时 {e640:.4f}")
    out["问题1最大偏差"] = {"N20": e20, "N640": e640}

    # ---------------- 问题 2 ----------------
    print()
    print("=" * 92)
    print("问题 2 逐点比对（同学论文表 3 / 我们的表 3、4）")
    print("=" * 92)
    o2_20 = run_p2(amb, 20)
    o2_640 = run_p2(amb, 640)
    print(f"{'t/h':>5} {'量':>5} | {'同学':>10} {'我们N=20':>10} {'差':>9} | "
          f"{'我们N=640':>10} {'差':>9}")
    p2_rows = []
    for h in sorted(CC_P2):
        cc = CC_P2[h]
        for j, name in enumerate(["T中心", "T表面", "C中心", "C表面"]):
            d20 = o2_20[h][j] - cc[j]
            d640 = o2_640[h][j] - cc[j]
            p2_rows.append((h, name, cc[j], o2_20[h][j], d20, o2_640[h][j], d640))
            print(f"{h:>5} {name:>5} | {cc[j]:>10.4f} {o2_20[h][j]:>10.4f} "
                  f"{d20:>+9.4f} | {o2_640[h][j]:>10.4f} {d640:>+9.4f}")
    out["问题2"] = [{"h": r[0], "量": r[1], "同学": r[2], "我们N20": r[3],
                     "差N20": r[4], "我们N640": r[5], "差N640": r[6]}
                    for r in p2_rows]
    e2_20 = max(abs(r[4]) for r in p2_rows)
    e2_640 = max(abs(r[6]) for r in p2_rows)
    print(f"\n最大绝对偏差：N=20 时 {e2_20:.5f}；N=640 时 {e2_640:.5f}")
    out["问题2最大偏差"] = {"N20": e2_20, "N640": e2_640}

    # ---------------- 问题 3：差异来源排查 ----------------
    print()
    print("=" * 92)
    print("问题 3 烘干时长：网格分辨率与界面平均方式的影响")
    print("=" * 92)
    print(f"同学论文（N=1280/2560，调和平均的保守型有限体积）：{CC_TIME['P3_h']:.4f} h")
    grid = {}
    print("\n[界面系数：算术平均]（我们原来的做法）")
    for n in [20, 40, 80, 160, 320]:
        t3 = drying_time(props3, D3, amb, n_cells=n, face_avg="arithmetic")
        grid[f"arith_{n}"] = t3
        txt = "20 天内未达标" if t3 is None else f"{t3:.4f} h"
        d = "" if t3 is None else f"（与同学差 {t3 - CC_TIME['P3_h']:+.4f} h）"
        print(f"  N = {n:>4} : {txt}   {d}")
    print("\n[界面系数：调和平均]（同学论文的做法）")
    harm = {}
    for n in [20, 80, 320]:
        t3 = drying_time(props3, D3, amb, n_cells=n, face_avg="harmonic")
        harm[f"harm_{n}"] = t3
        txt = "20 天内未达标" if t3 is None else f"{t3:.4f} h"
        d = "" if t3 is None else f"（与同学差 {t3 - CC_TIME['P3_h']:+.4f} h）"
        print(f"  N = {n:>4} : {txt}   {d}")
    out["问题3_网格与平均方式"] = {"算术平均": grid, "调和平均": harm,
                                   "同学": CC_TIME["P3_h"]}

    # ---------------- 问题 4 ----------------
    print()
    print("=" * 92)
    print("问题 4 烘干时长对比")
    print("=" * 92)
    p4 = {}
    for n in [20, 160]:
        for avg in ["arithmetic", "harmonic"]:
            t4 = drying_time(props4, D4, amb, n_cells=n, face_avg=avg,
                             R_fun=RadiusCurve())
            p4[f"{avg}_{n}"] = t4
            print(f"  {avg:>10}, N = {n:>4} : {t4:.4f} h  "
                  f"（同学 {CC_TIME['P4_h']:.4f} h，差 {t4 - CC_TIME['P4_h']:+.4f} h）")
    out["问题4"] = p4

    # ---------------- 收缩效应的正确分解 ----------------
    print()
    print("=" * 92)
    print("收缩效应的分解（同学论文的 11.10% 是把两个因素混在一起了）")
    print("=" * 92)
    t3_arith = drying_time(props3, D3, amb, n_cells=20)
    t4_noshrink = drying_time(props4, D4, amb, n_cells=20)
    t4_shrink = drying_time(props4, D4, amb, n_cells=20, R_fun=RadiusCurve())
    print(f"  A 附录3物性、无收缩（问题3）      : {t3_arith:.2f} h")
    print(f"  B 附录4物性、无收缩               : {t4_noshrink:.2f} h  "
          f"（换物性使时长 ×{t4_noshrink / t3_arith:.2f}）")
    print(f"  C 附录4物性、含收缩（问题4）      : {t4_shrink:.2f} h  "
          f"（收缩使时长 ×{t4_shrink / t4_noshrink:.2f}）")
    print(f"  同学口径 A->C 的降幅 {(t3_arith - t4_shrink) / t3_arith * 100:.2f}%"
          "（把物性变化和收缩混在一起）")
    print(f"  只看收缩 B->C 的降幅 {(t4_noshrink - t4_shrink) / t4_noshrink * 100:.2f}%")
    out["收缩分解"] = {"A_附录3无收缩_h": t3_arith, "B_附录4无收缩_h": t4_noshrink,
                       "C_附录4含收缩_h": t4_shrink,
                       "物性影响倍数": t4_noshrink / t3_arith,
                       "收缩影响倍数": t4_shrink / t4_noshrink,
                       "A到C降幅_pct": (t3_arith - t4_shrink) / t3_arith * 100,
                       "B到C降幅_pct": (t4_noshrink - t4_shrink) / t4_noshrink * 100}

    (LOG / "problem_a_result_07_reference_comparison_v01.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(f"\n结果已写入 {LOG / 'compare_with_cc.json'}")


if __name__ == "__main__":
    main()
