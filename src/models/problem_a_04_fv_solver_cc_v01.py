# -*- coding: utf-8 -*-
"""一维轴对称柱坐标（半径方向）的节点中心有限体积求解器。

控制方程（每单位轴向长度，公共因子 2*pi 已约去）：
    能量： rho*cp * dT/dt = (1/r) * d/dr( k * r * dT/dr )
    水分：          dC/dt = (1/r) * d/dr( D * r * dC/dr )

边界条件：
    r = 0 ： dT/dr = dC/dr = 0（轴对称）
    r = R ： -k * dT/dr = h * (T - T_air)
             -D * dC/dr = km_scale * km * (C - C_air)

初始条件： T(r,0) = T0，C(r,0) = C0（均匀）

离散方式
--------
节点 r_i = i*dr（i = 0..N），在节点周围取控制体积并做有限体积积分：
    a_i * [rho*cp]_i * dT_i/dt = G_{i+1/2} (T_{i+1} - T_i) - G_{i-1/2} (T_i - T_{i-1})
其中 a_i 为控制体积的"长度因子"：
    a_0 = dr^2/8（r=0 处的半个体积，自动消除 1/r 奇异性）
    a_i = r_i * dr（内部节点）
    a_N = (R^2 - (R - dr/2)^2) / 2（表面节点）
界面导热/导质系数 G_{i+1/2} = coef_{i+1/2} * r_{i+1/2} / dr，
表面 G = h*R（或 km*R），这样柱坐标的守恒性被严格保持。

时间推进采用全隐式（后向欧拉），非线性系数用 Picard 迭代处理，
每一步都严格满足离散守恒律。
"""

import numpy as np

try:                                   # 用 LAPACK 的带状求解器加速（存在则优先使用）
    from scipy.linalg import solve_banded as _solve_banded
except Exception:                      # pragma: no cover
    _solve_banded = None


def solve_tridiag(lo, di, up, rhs):
    """求解三对角方程组，优先使用 LAPACK，退化时使用自带的追赶法。"""
    if _solve_banded is not None and di.size >= 3:
        n = di.size
        ab = np.zeros((3, n))
        ab[0, 1:] = up[:-1]
        ab[1, :] = di
        ab[2, :-1] = lo[1:]
        return _solve_banded((1, 1), ab, rhs)
    return thomas(lo, di, up, rhs)


def thomas(lo, di, up, rhs):
    """追赶法（Thomas 算法）求解三对角线性方程组，就地返回解向量。"""
    n = di.size
    cp = np.zeros(n)
    dp = np.zeros(n)
    cp[0] = up[0] / di[0]
    dp[0] = rhs[0] / di[0]
    for i in range(1, n):
        m = di[i] - lo[i] * cp[i - 1]
        dp[i] = (rhs[i] - lo[i] * dp[i - 1]) / m
        if i < n - 1:
            cp[i] = up[i] / m
    x = np.empty(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


class CylinderFV:
    """圆柱（半径方向一维）非稳态传热传质有限体积模型。"""

    def __init__(self, R, n_cells, h, km, T0, C0, props, D_fun,
                 km_scale=1.0, relax=0.9, max_iter=80, tol=1.0e-11,
                 R_fun=None, face_avg="arithmetic"):
        self.face_avg = face_avg
        self.R0 = float(R)
        self.R_fun = R_fun
        self.R = self.R0 if R_fun is None else float(R_fun(0.0))
        self.n = int(n_cells)
        # 归一化坐标 xi = r / R(t)：用它可以把收缩的动边界映射到固定区间 [0,1]
        self.dxi = 1.0 / self.n
        self.xi = np.linspace(0.0, 1.0, self.n + 1)
        self.xi_f = self.xi[:-1] + 0.5 * self.dxi   # 内部界面 xi_{i+1/2}
        # 以下三个属性仅为兼容与输出方便保留（初始构型下的物理量）
        self.dr = self.R0 * self.dxi
        self.r = self.xi * self.R0
        self.rf = self.xi_f * self.R0
        self.h = float(h)
        self.km = float(km)
        self.km_scale = float(km_scale)
        self.props = props
        self.D_fun = D_fun
        self.relax = float(relax)
        self.max_iter = int(max_iter)
        self.tol = float(tol)

        # 控制体积长度因子 a_i（在 xi 坐标下的度量，与 R(t) 无关）
        a = np.empty(self.n + 1)
        a[0] = self.dxi ** 2 / 8.0
        a[1:self.n] = self.xi[1:self.n] * self.dxi
        a[self.n] = (1.0 - (1.0 - 0.5 * self.dxi) ** 2) / 2.0
        self.a = a

        self.T = np.full(self.n + 1, float(T0))
        self.C = np.full(self.n + 1, float(C0))
        self.T0 = float(T0)
        self.C0 = float(C0)
        self.t = 0.0

        # 账目记录（用于守恒校验）
        self.acc_heat_flux = 0.0     # 累计 积分 h*R*(T_air - T_surf) dt
        self.acc_mass_flux = 0.0     # 累计 积分 km*R*(C_air - C_surf) dt
        self.n_iters = []
        self.last_T_air = float(T0)
        self.last_C_air = float(C0)

    # ------------------------------------------------------------------
    def _assemble_field(self, cap, G, G_out, phi_old, phi_air):
        """组装三对角系统：cap_i * phi_i^{n+1} + sum(表面通量) = cap_i * phi_i^n。"""
        n = self.n
        lo = np.zeros(n + 1)
        di = np.zeros(n + 1)
        up = np.zeros(n + 1)
        rhs = np.zeros(n + 1)

        di[0] = cap[0] + G[0]
        up[0] = -G[0]
        rhs[0] = cap[0] * phi_old[0]

        di[1:n] = cap[1:n] + G[1:n] + G[0:n - 1]
        lo[1:n] = -G[0:n - 1]
        up[1:n] = -G[1:n]
        rhs[1:n] = cap[1:n] * phi_old[1:n]

        lo[n] = -G[n - 1]
        di[n] = cap[n] + G[n - 1] + G_out
        rhs[n] = cap[n] * phi_old[n] + G_out * phi_air
        return lo, di, up, rhs

    # ------------------------------------------------------------------
    def step(self, dt, T_air, C_air, R=None):
        """推进一个时间步（全隐式 + Picard 迭代），dt 单位 s。

        R 为当前时刻的半径（动边界收缩问题）；R = None 时按 R_fun(t+dt) 计算，
        没有 R_fun 则半径恒为 R0。半径只在系数里以 1/R^2（扩散项）和 1/R
        （表面通量项）出现，节点本身固定在 xi 网格上——即物质（拉格朗日）坐标，
        因此收缩时节点上的含水率不会发生虚假跳跃。
        """
        if R is None:
            if self.R_fun is None:
                R = self.R0
            else:
                R = float(self.R_fun(self.t + dt))
        self.R = float(R)
        T_old = self.T.copy()
        C_old = self.C.copy()
        T_it = T_old.copy()
        C_it = C_old.copy()

        G_out_h = self.h / self.R
        G_out_m = self.km_scale * self.km / self.R
        geom = 1.0 / (self.R ** 2 * self.dxi)       # 扩散项几何因子

        T_new = T_it
        C_new = C_it
        it = 0
        for it in range(1, self.max_iter + 1):
            rho, cp, k = self.props(T_it, C_it)
            D = self.D_fun(C_it, T_it)

            # --- 温度场 ---
            cap_h = self.a * rho * cp / dt
            if self.face_avg == "harmonic":
                k_face = 2.0 * k[:-1] * k[1:] / (k[:-1] + k[1:])
            else:
                k_face = 0.5 * (k[:-1] + k[1:])
            G_h = k_face * self.xi_f * geom
            lo, di, up, rhs = self._assemble_field(cap_h, G_h, G_out_h, T_old, T_air)
            T_new = solve_tridiag(lo, di, up, rhs)

            # --- 水分场 ---
            cap_m = self.a / dt
            if self.face_avg == "harmonic":
                D_face = 2.0 * D[:-1] * D[1:] / (D[:-1] + D[1:])
            else:
                D_face = 0.5 * (D[:-1] + D[1:])
            G_m = D_face * self.xi_f * geom
            lo, di, up, rhs = self._assemble_field(cap_m, G_m, G_out_m, C_old, C_air)
            C_new = solve_tridiag(lo, di, up, rhs)
            C_new = np.maximum(C_new, 0.0)

            err = max(np.max(np.abs(T_new - T_it)), np.max(np.abs(C_new - C_it)))
            if err < self.tol:
                T_it = T_new
                C_it = C_new
                break
            T_it = (1.0 - self.relax) * T_it + self.relax * T_new
            C_it = (1.0 - self.relax) * C_it + self.relax * C_new

        self.T = np.maximum(T_it, 0.0)
        self.C = np.maximum(C_it, 0.0)
        self.t += dt

        # 守恒账目：后向欧拉下界面通量取 n+1 时刻的值，此时离散守恒严格成立
        self.acc_heat_flux += G_out_h * (T_air - self.T[-1]) * dt
        self.acc_mass_flux += G_out_m * (C_air - self.C[-1]) * dt
        self.n_iters.append(it)
        self.last_T_air = float(T_air)
        self.last_C_air = float(C_air)
        return self.T, self.C

    # ------------------------------------------------------------------
    def check_balances(self):
        """返回 (能量相对残差, 水分相对残差)。

        离散能量守恒： sum(a_i * rho*cp * (T_i - T_i0)) = 积分 h*R*(T_air - T_surf) dt
        离散水分守恒： sum(a_i * (C_i - C_i0))         = 积分 km*R*(C_air - C_surf) dt
        后向欧拉下界面通量取 n+1 时刻值，上式对常物性问题应精确成立（机器精度）。
        """
        rho, cp, _ = self.props(self.T, self.C)
        e_now = float(np.sum(self.a * rho * cp * self.T))
        e_init = float(np.sum(self.a * rho * cp * self.T0))
        m_now = float(np.sum(self.a * self.C))
        m_init = float(np.sum(self.a * self.C0))
        e_res = (e_now - e_init - self.acc_heat_flux) / max(abs(e_now - e_init), 1e-30)
        m_res = (m_now - m_init - self.acc_mass_flux) / max(abs(m_now - m_init), 1e-30)
        return e_res, m_res

    def snapshot(self):
        return self.t, self.T.copy(), self.C.copy()
