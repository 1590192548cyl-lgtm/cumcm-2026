# -*- coding: utf-8 -*-
"""界面系数平均方式 × 网格分辨率 的收敛性对照。

目的有两个：
  1. 决定生产口径该用算术平均还是调和平均（两者在细网格上收敛到同一个值）；
  2. 补上极端 km_scale 下自己的网格收敛数据，而不是只依赖外部旁证。

输出 logs/convergence_face_avg.json
"""

import json
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
for _sub in ("preprocessing", "models", "analysis", "visualization"):
    sys.path.insert(0, str(ROOT / "src" / _sub))

from problem_a_12_compare_reference_cc_v01 import drying_time            # noqa: E402
from problem_a_03_properties_cc_v01 import props3, D3                       # noqa: E402
from problem_a_01_preprocess_cc_v01 import load_ambient                # noqa: E402

LOG = ROOT / "outputs" / "results"

# (km_scale, 网格层数列表) —— 只挑最有信息量的组合，控制总时长
CASES = [
    (1.0, [320, 640, 1280]),
    (820.0, [160, 320, 640]),
]
AVERAGES = ["arithmetic", "harmonic"]


def main():
    amb = load_ambient()
    out = {}
    print("=" * 84)
    print("问题 3 烘干时长（小时）：界面平均方式 × 网格层数 × km_scale")
    print("=" * 84)
    print(f"{'km_scale':>9} {'平均方式':>11} | " + " | ".join(
        f"{'N=' + str(n):>10}" for n in [160, 320, 640, 1280]))
    for ks, ns in CASES:
        for avg in AVERAGES:
            row = {}
            cells = []
            for n in [160, 320, 640, 1280]:
                if n not in ns:
                    cells.append(f"{'—':>10}")
                    continue
                t0 = time.time()
                t = drying_time(props3, D3, amb, n_cells=n, face_avg=avg,
                                dt=60.0, t_max=40 * 24 * 3600.0, km_scale=ks)
                row[f"N={n}"] = t
                cells.append(f"{'未达标' if t is None else f'{t:.2f}':>10}")
                print(f"    ... N={n} {avg} km={ks} 用时 {time.time() - t0:.0f} s",
                      flush=True)
            out[f"km{ks}_{avg}"] = row
            print(f"{ks:>9g} {avg:>11} | " + " | ".join(cells), flush=True)

    (LOG / "problem_a_result_03_convergence_face_avg_v01.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(f"\n已写入 {LOG / 'convergence_face_avg.json'}")


if __name__ == "__main__":
    main()
