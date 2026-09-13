# -*- coding: utf-8 -*-
"""生成 result2.xlsx 的"整个烘干过程、每 1 s"版本。

题目要求把"每隔 1 s、每隔 0.1 cm 的完整结果"写入 result2.xlsx，
而正文表 3、表 4 只取 3 h 内的抽样。两处口径不同，故同时产出两份：

    output/result2.xlsx          整个烘干过程（0 ~ 烘干结束），每 1 s
    output/extra/result2_3h.xlsx 仅 0 ~ 3 h，每 1 s（正文表的完整版）

时间步：0 ~ 3 h 用 0.1 s（保证四位小数），3 h 之后用 1 s（此时温度已均匀、
含水率变化极缓，1 s 步长的截断误差远低于 1e-4）。
用 openpyxl 的 write_only 模式逐行写出，避免上百万单元格占内存。
"""

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
from problem_a_01_preprocess_cc_v01 import load_ambient                      # noqa: E402
from problem_a_03_properties_cc_v01 import props3, D3                             # noqa: E402

OUT = ROOT / "outputs" / "submissions" / "problem_a"
C_THRESHOLD = 0.15


def main():
    amb = load_ambient()
    n_cells = cfg.N_CELLS
    idx = np.round(np.linspace(0.0, 1.0, cfg.N_OUT + 1) * n_cells).astype(int)
    model = CylinderFV(R=cfg.R0, n_cells=n_cells, h=cfg.H_CONV, km=cfg.KM_CONV,
                       T0=cfg.T_INIT, C0=cfg.C_INIT, props=props3, D_fun=D3,
                       km_scale=1.0, relax=0.7, max_iter=80, tol=1e-10)

    import openpyxl
    (OUT / "extra").mkdir(exist_ok=True)
    wb = openpyxl.Workbook(write_only=True)
    wsT = wb.create_sheet("温度")
    wsC = wb.create_sheet("水分浓度")
    header = ["时间\\到药材中心的距离"] + [round(0.1 * j, 1) for j in range(21)]
    wsT.append(list(header))
    wsC.append(list(header))

    t0 = time.time()
    t = 0.0
    n = 0
    # ---- 阶段 1：0 ~ 3 h，dt = 0.1 s，每 1 s 记一行 ----
    for k in range(1, 10801):
        for _ in range(10):
            n += 1
            model.step(0.1, amb.T_air(n * 0.1), amb.C_air(n * 0.1))
        t = k
        wsT.append([k] + [float(round(v, 4)) for v in model.T[idx]])
        wsC.append([k] + [float(round(v, 4)) for v in model.C[idx]])
    print(f"  0~3 h 完成（{n} 步），用时 {time.time() - t0:.0f} s", flush=True)

    # ---- 阶段 2：3 h ~ 烘干结束，dt = 1 s，每步记一行 ----
    t_end = None
    while t < 30 * 24 * 3600.0:
        t += 1.0
        n += 1
        model.step(1.0, amb.T_air(t), amb.C_air(t))
        wsT.append([int(round(t))] + [float(round(v, 4)) for v in model.T[idx]])
        wsC.append([int(round(t))] + [float(round(v, 4)) for v in model.C[idx]])
        if model.C.max() <= C_THRESHOLD:
            t_end = t
            break
        if int(t) % 36000 == 0:
            print(f"  t = {t / 3600:.0f} h，中心 C = {model.C[0]:.4f}，"
                  f"累计用时 {time.time() - t0:.0f} s", flush=True)
    wb.save(OUT / "result2.xlsx")
    print(f"  result2.xlsx 已写出：{int(t_end)} 行，"
          f"烘干结束 {t_end / 3600:.4f} h，总用时 {time.time() - t0:.0f} s")

    # ---- 3 h 版本另存 ----
    import shutil
    wb2 = openpyxl.Workbook(write_only=True)
    sT = wb2.create_sheet("温度")
    sC = wb2.create_sheet("水分浓度")
    src = openpyxl.load_workbook(OUT / "result2.xlsx", read_only=True)
    st, sc = src["温度"], src["水分浓度"]
    hdr = [c.value for c in next(st.iter_rows())]
    sT.append(hdr)
    sC.append(hdr)
    for i, (r1, r2) in enumerate(zip(st.iter_rows(min_row=2), sc.iter_rows(min_row=2))):
        if r1[0].value is None or r1[0].value > 10800:
            break
        sT.append([c.value for c in r1])
        sC.append([c.value for c in r2])
    wb2.save(OUT / "extra" / "result2_3h.xlsx")
    print(f"  3 h 版本已写出：{OUT / 'extra' / 'result2_3h.xlsx'}")


if __name__ == "__main__":
    main()
