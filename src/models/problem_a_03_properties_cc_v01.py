# -*- coding: utf-8 -*-
"""题目附录 3、附录 4 给出的经验公式，以及附件 2 的半径插值。

附录 3（问题 2、3）：
    rho = 650 + 128*C                          kg/m^3
    cp  = 1450 + 2736*C/(C+1)                  J/(kg·K)
    k   = 0.21 + 0.38*C/(C+1)                  W/(m·K)
    D   = 2.4e-3 * exp(-0.45/C) * exp(-3850/T) m^2/s，T 为开尔文

附录 4（问题 4，含收缩）：
    rho = 760 + 90*C
    cp  = 1850 + 2150*C/(C+1)
    k   = 0.12 + 0.20*C/(C+1)
    D   = 4.2e-4 * exp(-0.30/C) * exp(-3850/T)
"""

import numpy as np

import problem_a_02_config_cc_v01 as cfg
from problem_a_01_preprocess_cc_v01 import load_radius


def _arr(x):
    return np.asarray(x, dtype=float)


# ------------------------------------------------------------------ 附录 3
def props3(T, C):
    C = _arr(C)
    return (650.0 + 128.0 * C,
            1450.0 + 2736.0 * C / (C + 1.0),
            0.21 + 0.38 * C / (C + 1.0))


def D3(C, T):
    C = np.maximum(_arr(C), cfg.C_FLOOR)
    Tk = _arr(T) + 273.15
    return 2.4e-3 * np.exp(-0.45 / C) * np.exp(-3850.0 / Tk)


# ------------------------------------------------------------------ 附录 4
def props4(T, C):
    C = _arr(C)
    return (760.0 + 90.0 * C,
            1850.0 + 2150.0 * C / (C + 1.0),
            0.12 + 0.20 * C / (C + 1.0))


def D4(C, T):
    C = np.maximum(_arr(C), cfg.C_FLOOR)
    Tk = _arr(T) + 273.15
    return 4.2e-4 * np.exp(-0.30 / C) * np.exp(-3850.0 / Tk)


# ------------------------------------------------------------------ 收缩
class RadiusCurve:
    """附件 2 给出的半径随时间变化 R(t)，单位 cm -> m。

    数据只在 0~259200 s（3 天）内有值，超出后按端点常数外延。
    """

    def __init__(self):
        df = load_radius()
        self.t = df["时间_s"].to_numpy(float)
        self.R = df["半径_cm"].to_numpy(float) * 1.0e-2

    def __call__(self, t):
        return float(np.interp(t, self.t, self.R))

    @property
    def R0(self):
        return float(self.R[0])

    @property
    def R_end(self):
        return float(self.R[-1])
