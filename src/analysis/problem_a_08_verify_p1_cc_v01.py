# -*- coding: utf-8 -*-
"""问题 1 求解器的校验脚本。

四个层次的校验（对应论文"模型检验"一节）：
  校验 1  网格与时间步收敛性（自收敛，估计收敛阶）
  校验 2  与柱坐标解析解对比（常物性、恒定环境温度下的分离变量级数解）
  校验 3  离散守恒律残差（能量守恒、水分质量守恒）
  校验 4  关键参数灵敏度（对流传质系数口径 km_scale）
另外附 Picard 迭代收敛性记录。
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
from problem_a_05_run_p1_cc_v01 import solve, AmbientConst, setup_matplotlib  # noqa: E402
from problem_a_01_preprocess_cc_v01 import load_ambient                      # noqa: E402
from scipy.optimize import brentq                        # noqa: E402
from scipy.special import j0, j1                         # noqa: E402

LOG = ROOT / "outputs" / "results"
FIG = ROOT / "outputs" / "figures"


# --------------------------------------------------------------------------
# 解析解：无限长圆柱，常物性，第三类边界条件
#   theta = (T - T_inf)/(T0 - T_inf)
#         = sum_n A_n J0(beta_n * r/R) exp(-beta_n^2 * Fo)
#   beta_n 为 beta J1(beta) = Bi J0(beta) 的正根，
#   A_n = 2 J1(beta_n) / (beta_n (J0(beta_n)^2 + J1(beta_n)^2))
# --------------------------------------------------------------------------
def cylinder_eigenvalues(bi, n_roots=60):
    f = lambda b: b * j1(b) - bi * j0(b)
    roots = []
    x = 1.0e-4
    dx = 0.02
    while len(roots) < n_roots and x < 400.0:
        x2 = x + dx
        if f(x) * f(x2) < 0.0:
            roots.append(brentq(f, x, x2))
        x = x2
    return np.array(roots)


def cylinder_series(r, t, R, alpha, h, k, T0, Tinf, n_terms=30):
    bi = h * R / k
    beta = cylinder_eigenvalues(bi, n_terms)[:n_terms]
    xi = np.asarray(r, dtype=float) / R
    Fo = alpha * t / R ** 2
    A = 2.0 * j1(beta) / (beta * (j0(beta) ** 2 + j1(beta) ** 2))
    theta = np.zeros_like(xi)
    for m in range(beta.size):
        theta += A[m] * j0(beta[m] * xi) * np.exp(-beta[m] ** 2 * Fo)
    return Tinf + (T0 - Tinf) * theta


def main():
    LOG.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    out = {}
    print("=" * 74)
    print("校验 1  网格与时间步收敛性（t = 1800 s，与 0.1 cm 输出网格对齐）")
    print("=" * 74)

    # dt 必须整除输出间隔 1 s，solve() 的 steps 参数是"输出记录条数"
    levels = [(20, 1.0), (40, 0.5), (80, 0.25), (160, 0.125), (320, 0.0625),
              (640, 0.03125)]
    sols = {}
    for n, dt in levels:
        res = solve(steps=1800, dt=dt, n_cells=n)
        sols[(n, dt)] = dict(
            T=res["T"][-1], C=res["C"][-1],
            wall=res["wall"], iters=float(np.mean(res["model"].n_iters)),
        )
        print(f"  N={n:4d}, dt={dt:6.3f} s : 用时 {res['wall']:6.2f} s, "
              f"平均 Picard {np.mean(res['model'].n_iters):.1f} 次")

    conv = []
    keys = list(sols.keys())
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        dT = float(np.max(np.abs(sols[k0]["T"] - sols[k1]["T"])))
        dC = float(np.max(np.abs(sols[k0]["C"] - sols[k1]["C"])))
        conv.append({"coarse": list(k0), "fine": list(k1), "dT": dT, "dC": dC})
        print(f"  ({k0[0]:3d},{k0[1]:.3f}) -> ({k1[0]:3d},{k1[1]:.3f}) : "
              f"max|dT| = {dT:.3e} K, max|dC| = {dC:.3e} kg/kg")

    order_T = []
    for i in range(len(conv) - 1):
        e1, e2 = conv[i]["dT"], conv[i + 1]["dT"]
        if e2 > 0:
            p = np.log2(e1 / e2)
            order_T.append(float(p))
            print(f"    温度收敛阶估计 p = {p:.2f}")
    out["收敛性"] = {"逐级差": conv, "温度收敛阶": order_T}

    ref = sols[keys[-1]]
    res_prod = solve()                      # 实际生产设置：cfg.N_CELLS, cfg.DT
    prod = dict(T=res_prod["T"][-1], C=res_prod["C"][-1])
    out["生产网格_vs_参考网格"] = {
        "生产网格": [cfg.N_CELLS, cfg.DT],
        "参考网格": list(keys[-1]),
        "max|dT|": float(np.max(np.abs(prod["T"] - ref["T"]))),
        "max|dC|": float(np.max(np.abs(prod["C"] - ref["C"]))),
    }
    print(f"  生产网格 ({cfg.N_CELLS},{cfg.DT}) 与参考网格 {keys[-1]} 的偏差："
          f"max|dT| = {out['生产网格_vs_参考网格']['max|dT|']:.3e} K, "
          f"max|dC| = {out['生产网格_vs_参考网格']['max|dC|']:.3e} kg/kg")

    # ----------------------------------------------------------------------
    print()
    print("=" * 74)
    print("校验 2  与解析解对比（常物性、环境恒温 50 摄氏度）")
    print("=" * 74)
    Tinf = 50.0
    amb50 = AmbientConst(Tinf, 0.05)
    res50 = solve(ambient=amb50, n_cells=640, dt=0.0625, steps=1800)
    alpha = cfg.K_COND / (cfg.RHO * cfg.CP)
    r_coarse = np.linspace(0.0, cfg.R0, 21)
    T_ref = cylinder_series(r_coarse, 1800.0, cfg.R0, alpha,
                            cfg.H_CONV, cfg.K_COND, cfg.T_INIT, Tinf)
    T_num_fine = res50["T"][-1]
    res50_coarse = solve(ambient=amb50, n_cells=cfg.N_CELLS, dt=cfg.DT, steps=1800)
    T_num_prod = res50_coarse["T"][-1]
    e_fine = float(np.max(np.abs(T_num_fine - T_ref)))
    e_prod = float(np.max(np.abs(T_num_prod - T_ref)))
    print(f"  解析解 vs 细网格数值解 (640, 0.0625)：max 偏差 = {e_fine:.4e} K")
    print(f"  解析解 vs 生产网格数值解 ({cfg.N_CELLS}, {cfg.DT})：max 偏差 = "
          f"{e_prod:.4e} K")
    print(f"  参考：整个过程的温升幅度 = {Tinf - cfg.T_INIT:.1f} K")

    # 解析解自检：Fo = 0 时级数应处处等于初值，即 sum_n A_n J0(beta_n*xi) = 1
    beta_chk = cylinder_eigenvalues(cfg.H_CONV * cfg.R0 / cfg.K_COND, 30)
    A_chk = 2.0 * j1(beta_chk) / (beta_chk * (j0(beta_chk) ** 2 + j1(beta_chk) ** 2))
    xi_chk = np.linspace(0.0, 1.0, 11)
    series_at_0 = np.array([float(np.sum(A_chk * j0(beta_chk * x))) for x in xi_chk])
    out["解析解对比"] = {
        "细网格最大偏差_K": e_fine,
        "生产网格最大偏差_K": e_prod,
        "温升幅度_K": Tinf - cfg.T_INIT,
        "解析解系数自检_Fo0_最大偏差": float(np.max(np.abs(series_at_0 - 1.0))),
    }
    print(f"  解析解自检（Fo = 0 时级数应等于 1）：最大偏差 = "
          f"{out['解析解对比']['解析解系数自检_Fo0_最大偏差']:.2e}")

    # ----------------------------------------------------------------------
    print()
    print("=" * 74)
    print("校验 3  离散守恒律残差（生产网格）")
    print("=" * 74)
    res = solve()
    e_res, m_res = res["model"].check_balances()
    print(f"  能量守恒相对残差 = {e_res:.3e}")
    print(f"  水分质量守恒相对残差 = {m_res:.3e}")
    out["守恒残差"] = {"能量": e_res, "水分": m_res}

    # ----------------------------------------------------------------------
    print()
    print("=" * 74)
    print("校验 4  对流传质系数口径的灵敏度（t = 1800 s 的表面含水率）")
    print("=" * 74)
    sens = {}
    for ks in [0.1, 1.0, 10.0, 820.0]:
        r_ = solve(km_scale=ks)
        sens[str(ks)] = {
            "表面水分浓度": float(r_["C"][-1, -1]),
            "中心水分浓度": float(r_["C"][-1, 0]),
        }
        print(f"  km_scale = {ks:7.1f} : 表面 C = {r_['C'][-1, -1]:.4f}, "
              f"中心 C = {r_['C'][-1, 0]:.4f}")
    out["km_scale灵敏度"] = sens
    out["备注"] = ("km_scale = 1 表示采用与温度场完全类比的第三类边界条件 "
                   "-D dC/dr = km (C_s - C_a)；km_scale = 820 相当于把 km 折算为 "
                   "rho_dry*km 的通量口径。该口径是本题最大的建模不确定性来源，"
                   "需在论文中显式声明。")

    # ----------------------------------------------------------------------
    print()
    print("=" * 74)
    print("附加  Picard 迭代工作量")
    print("=" * 74)
    it_stats = {
        "平均迭代次数": float(np.mean(res["model"].n_iters)),
        "最大迭代次数": int(max(res["model"].n_iters)),
        "上限": int(res["model"].max_iter),
        "是否全部收敛": bool(max(res["model"].n_iters) < res["model"].max_iter),
    }
    out["Picard迭代"] = it_stats
    print(f"  平均 {it_stats['平均迭代次数']:.2f} 次/步，最大 "
          f"{it_stats['最大迭代次数']} 次（上限 {it_stats['上限']}），"
          f"全部收敛：{it_stats['是否全部收敛']}")

    # ----------------------------------------------------------------------
    (LOG / "problem_a_result_02_verification_v01.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    # 图：解析解对比 + 收敛性
    plt = setup_matplotlib()
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(r_coarse * 100, T_ref, "k-", lw=2, label="解析解（级数）")
    ax[0].plot(r_coarse * 100, T_num_prod, "o", ms=4, mfc="none",
               label=f"数值解 (N={cfg.N_CELLS}, dt={cfg.DT})")
    ax[0].plot(r_coarse * 100, T_num_fine, "x", ms=5,
               label="数值解 (N=640, dt=0.0625)")
    ax[0].set_xlabel("到药材中心的距离 / cm")
    ax[0].set_ylabel("温度 / 摄氏度")
    ax[0].set_title(f"恒定环境温度 50 摄氏度下 t = 1800 s 的温度分布\n"
                    f"（最大偏差 {e_prod:.2e} K）")
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=0.3)

    eT = [c["dT"] for c in conv]
    eC = [c["dC"] for c in conv]
    x = np.arange(len(eT))
    ax[1].semilogy(x, eT, "o-", label="温度 max|差| / K")
    ax[1].semilogy(x, eC, "s-", label="含水率 max|差| / (kg/kg)")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([f"({k0[0]},{k0[1]})->({k1[0]},{k1[1]})"
                           for k0, k1 in zip(keys[:-1], keys[1:])], fontsize=7)
    ax[1].set_ylabel("相邻网格解的最大偏差")
    ax[1].set_title("网格与时间步收敛性")
    ax[1].legend(fontsize=8)
    ax[1].grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(FIG / "p1_verification.png", dpi=160)
    plt.close(fig)
    print(f"\n  校验结果已写入 {LOG / 'verify_p1.json'}")
    print(f"  校验图已写入 {FIG / 'p1_verification.png'}")


if __name__ == "__main__":
    main()
