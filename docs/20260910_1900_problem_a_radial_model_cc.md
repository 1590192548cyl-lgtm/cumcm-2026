# A 题问题 1：径向传热传质试算口径

## 建模范围

将长度为 $25\,\mathrm{cm}$、半径为 $2\,\mathrm{cm}$ 的药材近似为长圆柱。问题只要求输出到圆柱中心的径向距离，因此第一版忽略轴向梯度，求解一维轴对称径向温度场与干基含水率场。长度与半径之比为 $L/R=12.5$，该近似适合作为问题 1 的第一版模型，但后续仍应以二维轴对称模型进行端部效应敏感性检验。

## 控制方程

温度满足

$$
\rho c_p\frac{\partial T}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left(rk\frac{\partial T}{\partial r}\right).
$$

干基含水率满足

$$
\frac{\partial C}{\partial t}
=\frac{1}{r}\frac{\partial}{\partial r}
\left(rD(C)\frac{\partial C}{\partial r}\right),
\qquad
D(C)=7\times10^{-9}\exp\left(-\frac{0.89}{C}\right).
$$

初始条件为

$$
T(r,0)=28\,^{\circ}\mathrm{C},\qquad C(r,0)=2.55\,\mathrm{kg/kg}.
$$

中心采用对称边界：

$$
\left.\frac{\partial T}{\partial r}\right|_{r=0}=0,
\qquad
\left.\frac{\partial C}{\partial r}\right|_{r=0}=0.
$$

表面采用第三类边界：

$$
k\left.\frac{\partial T}{\partial r}\right|_{r=R}
=h\bigl[T_{\infty}(t)-T(R,t)\bigr],
$$

$$
D(C_s)\left.\frac{\partial C}{\partial r}\right|_{r=R}
=h_m\bigl[C_{\infty}(t)-C(R,t)\bigr].
$$

炉内温度 $T_{\infty}(t)$ 与空气含湿量 $C_{\infty}(t)$ 由附件 1 的离散观测作分段线性插值。

## 数值方法与检查

径向采用节点中心有限体积法，使中心奇点和表面通量都以守恒形式处理；时间积分采用隐式 BDF 方法。为解析最初数秒在表面形成的很薄水分边界层，最终计算采用 $2560$ 个径向区间，内部网格步长为 $0.00078125\,\mathrm{cm}$，再抽取题目要求的 $0.1\,\mathrm{cm}$ 输出网格。使用 $640$、$1280$、$2560$ 个径向区间比较网格收敛，并检查由表面通量积分得到的总体热量、水分变化是否与域内平均值变化一致。

## 当前局限

本试算尚未把端面传热传质、体积收缩和温度对水分扩散系数的影响纳入问题 1。正式论文中应说明这些假设，并在后续问题或稳健性检验中逐步放宽。
