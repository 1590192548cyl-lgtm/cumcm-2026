# -*- coding: utf-8 -*-
"""极端 km_scale 下的进一步网格加密：判断调和平均究竟收敛到哪里。

上一轮得到 km_scale=820 时 调和平均 315.86 / 174.75 / 106.42 (N=160/320/640)，
随网格加密单调下降、尚未收敛。本脚本补到 N=2560，看是否收敛到与算术平均相同的值。
（两种平均都是相容格式，理论上必须收敛到同一个 PDE 真解。）
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

# (km_scale, 平均方式, 网格层数)
CASES = []
for n in [1280, 2560]:
    CASES += [(820.0, "harmonic", n), (820.0, "arithmetic", n),
              (1.0, "harmonic", n), (1.0, "arithmetic", n)]


def main():
    amb = load_ambient()
    out = {}
    print("=" * 70)
    print("加密到 N=1280 / 2560")
    print("=" * 70)
    for ks, avg, n in CASES:
        t0 = time.time()
        t = drying_time(props3, D3, amb, n_cells=n, face_avg=avg, dt=60.0,
                        t_max=40 * 24 * 3600.0, km_scale=ks)
        out[f"km{ks}_{avg}_N{n}"] = t
        print(f"  km_scale={ks:>6g}  {avg:>11}  N={n:>5}  -> "
              f"{'未达标' if t is None else f'{t:.3f} h':>12}   ({time.time() - t0:.0f} s)",
              flush=True)
    (LOG / "problem_a_result_04_convergence_extreme_v01.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(f"\n已写入 {LOG / 'convergence_extreme.json'}")


if __name__ == "__main__":
    main()
