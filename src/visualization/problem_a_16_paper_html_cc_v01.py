# -*- coding: utf-8 -*-
"""把论文排版成 HTML，再用 Chrome/Edge 无头模式打印成 PDF。

本机没有可用的 LaTeX 发行版（MiKTeX 安装残缺），因此用 HTML + MathJax(SVG)
作为排版路径：公式用 LaTeX 语法写、由本地 MathJax 渲染成 SVG，
表格由结果 CSV 直接生成，插图以 base64 内嵌，最后交给浏览器分页打印。

用法：
    python src/make_paper_html.py            # 生成 paper/paper.html 并打印 PDF
"""

import base64
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
for _sub in ("preprocessing", "models", "analysis", "visualization"):
    sys.path.insert(0, str(ROOT / "src" / _sub))

OUT = ROOT / "outputs" / "submissions" / "problem_a"
LOG = ROOT / "outputs" / "results"
PAPER = ROOT / "paper"
FIG = PAPER / "figures"

CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]


def img64(name):
    return base64.b64encode((FIG / f"{name}.png").read_bytes()).decode()


def table_html(csv_name, caption, time_head="时间"):
    rows = list(csv.reader((ROOT / "outputs" / "tables" / f"{csv_name}.csv").open(encoding="utf-8-sig")))
    head, body = rows[0], rows[1:]
    cols = [c.replace("cm", "") for c in head[1:]]
    h = f'<table><caption>表 &nbsp;{caption}</caption><thead><tr><th>{time_head}</th>'
    h += "".join(f"<th>{c}</th>" for c in cols) + "</tr></thead><tbody>"
    for r in body:
        t = float(r[0])
        tv = f"{t:.0f}" if abs(t - round(t)) < 1e-9 else f"{t:.2f}"
        h += f"<tr><td>{tv}</td>"
        for c in r[1:]:
            if c in ("", "nan"):
                h += "<td>--</td>"
            else:
                h += f"<td>{float(c):.4f}</td>"
        h += "</tr>"
    return h + "</tbody></table>"


def figure(name, caption, width="100%"):
    return (f'<figure><img src="data:image/png;base64,{img64(name)}" style="width:{width}">'
            f'<figcaption>{caption}</figcaption></figure>')


CSS = """
@page { size: A4; margin: 22mm 20mm 20mm 20mm; }
html { -webkit-print-color-adjust: exact; }
body { font-family: "Times New Roman", SimSun, serif; font-size: 11.5pt;
       line-height: 1.62; color: #000; margin: 0; }
h1.title { font-size: 17pt; text-align: center; font-family: SimHei, sans-serif;
           margin: 0 0 14px 0; line-height: 1.4; }
h2 { font-size: 13.5pt; font-family: SimHei, sans-serif; margin: 16px 0 6px; }
h3 { font-size: 12pt; font-family: SimHei, sans-serif; margin: 12px 0 4px; }
p { margin: 5px 0; text-align: justify; text-indent: 2em; }
p.noind, .abstract p { text-indent: 0; }
.abstract { border: 1px solid #888; padding: 8px 12px; margin: 10px 0 6px;
            background: #fafafa; }
.abstract h2 { text-align: center; margin-top: 0; }
.kw { text-indent: 0; margin-top: 6px; }
table { border-collapse: collapse; margin: 8px auto 10px; font-size: 10pt;
        width: 100%; }
caption { font-size: 10.5pt; font-family: SimHei, sans-serif; padding-bottom: 4px; }
th, td { border: 1px solid #333; padding: 2px 3px; text-align: center; }
thead th { background: #eef1f5; font-weight: normal; }
figure { margin: 10px 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 10.5pt; font-family: SimHei, sans-serif; margin-top: 3px; }
ul, ol { margin: 5px 0 5px 0; padding-left: 2em; }
li { margin: 2px 0; text-align: justify; }
mjx-container[display="true"] { margin: 8px 0 !important; }
.ref { font-size: 10pt; }
.ref p { text-indent: 0; margin: 3px 0; padding-left: 2em; text-indent: -2em; }
h2, h3 { page-break-after: avoid; }
"""


def main():
    H = []
    A = H.append
    A('<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">')
    A("<title>药材的烘干问题</title>")
    A("<style>" + CSS + "</style>")
    A(r"""<script>
window.MathJax = {
  tex: { inlineMath: [['\\(','\\)']], displayMath: [['\\[','\\]']] },
  svg: { fontCache: 'local' },
  startup: { typeset: true }
};
</script>""")
    A('<script src="mathjax_tex_svg.js" id="MathJax-script"></script>')
    A("</head><body>")
    A('<h1 class="title">基于守恒有限体积法的圆柱药材热湿传递与收缩干燥模型</h1>')

    # ---------------- 摘要 ----------------
    A('<div class="abstract"><h2>摘&nbsp;&nbsp;要</h2>')
    A("<p>热风干燥中，药材内部的径向传热与水分迁移决定升温速度和最终达标时刻。"
      "本文将圆柱药材简化为轴对称一维径向区域，建立径向导热方程与非线性水分扩散方程；"
      "表面采用对流换热与对流传质边界，烘房温湿度按附件 1 分段线性插值。"
      "物性随问题递进：问题 1 取附录 2 的常数热物性并保留题给的浓度相关扩散系数，"
      "问题 2、3 改用附录 3 的经验关系，问题 4 改用附录 4 并以 \\(\\xi=r/R(t)\\) "
      "为物质坐标处理收缩域，\\(R(t)\\) 由附件 2 插值得到。"
      "空间离散采用节点中心守恒有限体积格式，时间推进为全隐式，"
      "非线性系数由 Picard 迭代更新。</p>")
    A("<p>计算得到：预热 1800&nbsp;s 时药材中心与表面温度分别为 33.5755&nbsp;℃ 与 "
      "36.7856&nbsp;℃，相应干基含水率为 2.5500 与 1.5102&nbsp;kg/kg。"
      "固定半径时中心是最后达标位置，烘干时长 57.21&nbsp;h；计入附件 2 的收缩路径后为 "
      "50.86&nbsp;h，结束时半径约 1.200&nbsp;cm，在同一物性下收缩使烘干时间减少约 61%。"
      "网格加密到 2560 层后，问题 3 的烘干时长在 57.22&nbsp;h 收敛，"
      "算术与调和两种界面平均方式给出同一结果，说明结论与离散细节无关。"
      "文章另给出传质口径灵敏度、两阶段切换点灵敏度和蒸发潜热的量级审计，"
      "指出题给的热、质边界在缺少干物质密度与平衡含水率关系时不能机械拼合。</p>")
    A('<p class="kw"><b>关键词：</b>圆柱干燥；热湿传递；有限体积法；移动边界；'
      "网格收敛；灵敏度分析</p>")
    A("</div>")

    # ---------------- 1 问题重述与分析 ----------------
    A("<h2>1&nbsp;&nbsp;问题重述与分析</h2>")
    A("<h3>1.1&nbsp;&nbsp;问题重述</h3>")
    A("<p>研究对象为长 25&nbsp;cm、初始半径 2&nbsp;cm 的近似圆柱形中药材，"
      "初始温度 28&nbsp;℃，初始干基含水率 2.55&nbsp;kg/kg。"
      "题目按四个层次提出要求：问题 1 在预热平衡阶段建立温度场与水分浓度场的变化模型，"
      "并给出 1800&nbsp;s 内每 1&nbsp;s、距中心每 0.1&nbsp;cm 的完整结果；"
      "问题 2 建立整个烘干过程的模型，给出 3&nbsp;h 内的结果；"
      "问题 3 在固定半径条件下确定各处水分浓度均低于 0.15&nbsp;kg/kg 的首次时刻；"
      "问题 4 依据附件 2 的半径变化与附录 4 的物性关系，重新确定烘干时长。"
      "四个问题分别要求把结果写入指定的 Excel 文件。</p>")
    A("<h3>1.2&nbsp;&nbsp;问题分析</h3>")
    A("<p>模型能否降为一维，先看几何。药材长径比为 \\(25/(2\\times2)=12.5\\)，"
      "圆柱两端面积只占侧面积的 4%，题目又只要求到中心的径向距离，"
      "因此忽略轴向梯度，以半径 \\(r\\) 描述场变量。</p>")
    A("<p>是否需要计算内部梯度，看作热 Biot 数</p>")
    A(r"\[ Bi=\frac{hR_0}{k}=\frac{25\times0.02}{0.36}=1.39 \]")
    A("<p>它等于内部导热热阻与表面换热热阻之比。\\(Bi\\) 远大于 0.1，"
      "集总参数法不适用，必须求解分布参数模型，这与题目要求给出"
      "从中心到表面一整条分布一致。</p>")
    A("<p>两阶段的划分依据是 Luikov 数</p>")
    A(r"\[ Lu=\frac{D}{\alpha}=\frac{4.94\times10^{-9}}{0.36/(820\times2600)}=0.029 \]")
    A("<p>即热扩散比水分扩散快约 34 倍。热扩散特征时间 \\(R_0^2/\\alpha\\approx40\\)&nbsp;min，"
      "水分扩散特征时间 \\(R_0^2/D\\approx22\\)&nbsp;h，所以温度先趋于均匀，水分缓慢下降。"
      "由此可以预判问题 1 在 1800&nbsp;s 内温度场走完一轮瞬态，"
      "而含水率只有表层发生变化。</p>")
    A("<p>问题 2 之后物性随含水率和温度改变，方程由拟线性转为完全非线性；"
      "问题 4 的计算域随时间缩小。四问构成一条递进的模型链，共用同一组控制方程，"
      "差别只在物性关系、边界条件与几何。</p>")

    # ---------------- 2 模型假设 ----------------
    A("<h2>2&nbsp;&nbsp;模型假设</h2><ol>")
    for t in [
        "药材在任一横截面上轴对称，轴向梯度与端面传热传质忽略，场变量只依赖 \\(r\\) 与 \\(t\\)。",
        "药材内部无体积热源与水分源；水分在内部以扩散方式迁移，用 Fick 型方程描述，"
        "浓度变量取题目定义的干基含水率。",
        "表面与热风之间分别满足对流换热与对流传质边界。题目只在附录 2 给出 \\(h\\) 与 \\(h_m\\)，"
        "问题 2~4 未另给，故四问沿用同一组数值。",
        "附件 1、2 的离散序列在观测点之间分段线性变化；附件 1 只覆盖 0~14400&nbsp;s，"
        "其后按末次观测值保持恒定。",
        "问题 4 的收缩在径向上均匀发生，长度维持 25&nbsp;cm，\\(\\xi\\) 标记随材料运动的物质点。",
        "主模型把题给的热、质边界视为分别标定的等效闭合，不向能量方程叠加蒸发潜热项。"
        "题目未给干物质密度、平衡含水率关系与有效汽化潜热，直接耦合会导致量纲口径"
        "与能量供需不一致；第 10.5 节给出量级审计。",
    ]:
        A(f"<li>{t}</li>")
    A("</ol>")

    # ---------------- 3 符号说明 ----------------
    A("<h2>3&nbsp;&nbsp;符号说明</h2>")
    A("<table><caption>表 1&nbsp;&nbsp;主要符号与单位</caption><thead><tr>"
      "<th>符号</th><th>含义</th><th>单位</th><th>符号</th><th>含义</th></tr></thead><tbody>")
    for a, b, c, d, e in [
        ("\\(r\\)", "到中心轴的径向距离", "m", "\\(R(t)\\)", "药材瞬时半径 / m"),
        ("\\(\\xi\\)", "物质坐标，\\(\\xi=r/R(t)\\)", "1", "\\(t\\)", "时间 / s"),
        ("\\(T\\)", "药材温度", "℃", "\\(C\\)", "干基含水率 / (kg/kg)"),
        ("\\(T_\\infty\\)", "烘房空气温度", "℃", "\\(C_\\infty\\)", "空气水分浓度 / (kg/kg)"),
        ("\\(\\rho\\)", "药材密度", "kg/m³", "\\(c_p\\)", "定压比热容 / (J/(kg·K))"),
        ("\\(k\\)", "导热系数", "W/(m·K)", "\\(D\\)", "水分扩散系数 / (m²/s)"),
        ("\\(h\\)", "对流换热系数", "W/(m²·K)", "\\(h_m\\)", "对流传质系数 / (m/s)"),
    ]:
        A(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td></tr>")
    A("</tbody></table>")
    A("<p class=\"noind\">除特别说明外，温度单位用摄氏度，含水率用 kg/kg，长度用米；"
      "扩散系数以温度的开尔文值代入经验式。</p>")

    # ---------------- 4 模型建立 ----------------
    A("<h2>4&nbsp;&nbsp;模型建立</h2>")
    A("<h3>4.1&nbsp;&nbsp;控制方程</h3>")
    A("<p>在半径 \\(r\\) 处取厚度 \\(\\mathrm{d}r\\)、轴向单位长度的圆环微元。"
      "按能量守恒，单位时间从内侧流入的热量减去从外侧流出的热量等于微元内焓的增长率；"
      "按质量守恒，同样的收支关系适用于水分。将 Fourier 定律 "
      "\\(q=-k\\,\\partial T/\\partial r\\) 与 Fick 定律 "
      "\\(J=-D\\,\\partial C/\\partial r\\) 代入并取 \\(\\mathrm{d}r\\to0\\)，得</p>")
    A(r"\[ \rho(C)c_p(C)\frac{\partial T}{\partial t}=\frac{1}{r}\frac{\partial}{\partial r}\left(rk(C)\frac{\partial T}{\partial r}\right), \]")
    A(r"\[ \frac{\partial C}{\partial t}=\frac{1}{r}\frac{\partial}{\partial r}\left(rD(C,T)\frac{\partial C}{\partial r}\right). \]")
    A("<p>算子展开后为 \\(\\partial^2/\\partial r^2+(1/r)\\partial/\\partial r\\)，"
      "第二项是圆柱几何的曲率修正：半径越大，同样的热量分摊到更长的圆周上，"
      "温度变化率越小。</p>")
    A("<p>初始条件为 \\(T(r,0)=28\\,^\\circ\\mathrm{C}\\)，\\(C(r,0)=2.55\\,\\mathrm{kg/kg}\\)。</p>")

    A("<h3>4.2&nbsp;&nbsp;边界条件与物性关系</h3>")
    A("<p>中心处由轴对称性给出</p>")
    A(r"\[ \left.\frac{\partial T}{\partial r}\right|_{r=0}=0,\qquad \left.\frac{\partial C}{\partial r}\right|_{r=0}=0. \]")
    A("<p>表面处内部通量与外部通量相等，得到第三类边界条件</p>")
    A(r"\[ -k\left.\frac{\partial T}{\partial r}\right|_{r=R}=h\left[T(R,t)-T_\infty(t)\right],\qquad -D\left.\frac{\partial C}{\partial r}\right|_{r=R}=h_m\left[C(R,t)-C_\infty(t)\right], \]")
    A("<p>其中 \\(T_\\infty(t)\\)、\\(C_\\infty(t)\\) 由附件 1 分段线性插值给出。"
      "四问的物性关系按题目附录取用，见表 2。</p>")
    A("<table><caption>表 2&nbsp;&nbsp;各问的物性关系</caption><thead><tr>"
      "<th>问题</th><th>密度 \\(\\rho\\) / (kg/m³)</th><th>比热容 \\(c_p\\) / (J/(kg·K))</th>"
      "<th>导热系数 \\(k\\) / (W/(m·K))</th></tr></thead><tbody>")
    for q, a, b, c in [
        ("1", "\\(820\\)", "\\(2600\\)", "\\(0.36\\)"),
        ("2, 3", "\\(650+128C\\)", "\\(1450+2736\\dfrac{C}{C+1}\\)",
         "\\(0.21+0.38\\dfrac{C}{C+1}\\)"),
        ("4", "\\(760+90C\\)", "\\(1850+2150\\dfrac{C}{C+1}\\)",
         "\\(0.12+0.20\\dfrac{C}{C+1}\\)"),
    ]:
        A(f"<tr><td>{q}</td><td>{a}</td><td>{b}</td><td>{c}</td></tr>")
    A("</tbody></table>")
    A("<p>水分扩散系数分别为</p>")
    A(r"\[ D_1=7\times10^{-9}e^{-0.89/C},\qquad D_{2,3}=2.4\times10^{-3}e^{-0.45/C}e^{-3850/T_K},\qquad D_4=4.2\times10^{-4}e^{-0.30/C}e^{-3850/T_K}, \]")
    A("<p>其中 \\(T_K=T+273.15\\)。\\(e^{-a/C}\\) 随含水率下降而衰减，"
      "\\(e^{-3850/T_K}\\) 为 Arrhenius 形式的温度依赖。"
      "这两项使 \\(D\\) 在烘干全程变化两到三个数量级。</p>")

    A("<h3>4.3&nbsp;&nbsp;收缩域的物质坐标变换</h3>")
    A("<p>设无量纲物质坐标 \\(\\xi=r/R(t)\\in[0,1]\\)。干基含水率以单位干物料质量定义，"
      "均匀收缩时干物质总量守恒，在 \\(\\xi\\) 坐标下 \\(\\int\\xi\\,\\mathrm{d}\\xi\\) "
      "对应的干物料质量与 \\(t\\) 无关。对守恒律做变量替换，得</p>")
    A(r"\[ \frac{\partial C}{\partial t}=\frac{1}{\xi R^2(t)}\frac{\partial}{\partial\xi}\left(\xi D\frac{\partial C}{\partial\xi}\right),\qquad \frac{\partial T}{\partial t}=\frac{1}{\xi R^2(t)}\frac{\partial}{\partial\xi}\left(\xi\frac{k}{\rho c_p}\frac{\partial T}{\partial\xi}\right). \]")
    A("<p>变换后的方程不含对流项，半径只以 \\(1/R^2\\) 的形式进入扩散项；"
      "表面通量项相应地变为 \\(h/R\\) 与 \\(h_m/R\\)。"
      "物理含义是：同样的 \\(\\xi\\) 间隔对应实际距离 \\(R\\,\\mathrm{d}\\xi\\)，"
      "半径缩小时扩散路径变短，等效扩散加快。若改用当前半径 \\(r\\) 作自变量，"
      "则必须补入固体运动带来的对流项，两种写法等价。"
      "用物质坐标还避免半径缩小时节点上的含水率出现虚假跳跃。</p>")

    # ---------------- 5 数值方法 ----------------
    A("<h2>5&nbsp;&nbsp;数值方法</h2>")
    A("<h3>5.1&nbsp;&nbsp;节点中心守恒有限体积离散</h3>")
    A("<p>把 \\([0,1]\\) 划分为 \\(N\\) 个等长单元，节点 \\(\\xi_i=i/N\\)，"
      "\\(i=0,\\dots,N\\)。围绕每个节点取控制体并积分。"
      "记控制体的长度因子 \\(a_i=\\int\\xi\\,\\mathrm{d}\\xi\\)，则</p>")
    A(r"\[ a_0=\frac{\Delta\xi^2}{8},\qquad a_i=\xi_i\Delta\xi\ (1\le i\le N-1),\qquad a_N=\frac{1-(1-\Delta\xi/2)^2}{2}. \]")
    A("<p>以含水率为例，全隐式离散为</p>")
    A(r"\[ a_i\frac{C_i^{n+1}-C_i^n}{\Delta t}=G_{i+\frac12}\left(C_{i+1}^{n+1}-C_i^{n+1}\right)-G_{i-\frac12}\left(C_i^{n+1}-C_{i-1}^{n+1}\right),\qquad G_{i+\frac12}=\frac{D_{i+\frac12}\,\xi_{i+\frac12}}{R^2\Delta\xi}. \]")
    A("<p>温度方程结构相同，只需把 \\(D\\) 换成 \\(k\\)，并在时间项中乘以 \\(\\rho c_p\\)。"
      "这一写法有三点好处：中心节点的控制体是半径 \\(\\Delta\\xi/2\\) 的半个圆盘，"
      "其内侧面通量为零，\\(1/r\\) 的奇异性不出现在离散方程中；"
      "相邻控制体界面上的通量大小相等方向相反，全域求和时中间项相互抵消，"
      "离散守恒律精确成立；表面节点直接落在 \\(\\xi=1\\) 上，无需外推。</p>")
    A("<p>界面系数 \\(D_{i+1/2}\\) 取相邻节点值的算术平均。"
      "该选择依据第 10.3 节的收敛对照：算术平均与调和平均都是相容格式，"
      "网格加密后收敛到同一结果，而在本文采用的 640 层网格上算术平均的偏差更小。</p>")

    A("<h3>5.2&nbsp;&nbsp;时间推进与阈值事件判定</h3>")
    A("<p>时间方向采用后向欧拉（全隐式）。显式格式在 0.1&nbsp;cm 网格下的稳定上限"
      "约为 1.5&nbsp;s，而问题 3、4 需积分两百余小时，隐式是必需的。"
      "每步内的非线性系数由 Picard 迭代更新，收敛容差取 \\(10^{-10}\\)。</p>")
    A("<p>后向欧拉是一阶格式，时间步误差需单独控制。"
      "以恒定 50&nbsp;℃ 环境下的常物性解析解为基准，时间步 1&nbsp;s 时生产网格的"
      "最大偏差为 \\(3.9\\times10^{-3}\\)&nbsp;℃，恰在四位小数的量级上；"
      "改取 0.1&nbsp;s 后降为 \\(3.9\\times10^{-4}\\)&nbsp;℃。"
      "因此问题 1、2 的内部步长取 0.1&nbsp;s，输出仍按题目要求每 1&nbsp;s 抽样；"
      "问题 3、4 的预热段取 1&nbsp;s、恒温段取 60&nbsp;s，"
      "该步长下的烘干时长与 15&nbsp;s 相比相差 0.09%。</p>")
    A("<p>烘干终点的判据是全场含水率首次低于 0.15&nbsp;kg/kg，等价于中心节点首次达标。"
      "为避免判定时刻被离散时间层量化，在跨越阈值的两层之间做线性插值，"
      "得到连续意义下的达标时刻。</p>")

    # ---------------- 6 问题 1 ----------------
    A("<h2>6&nbsp;&nbsp;问题 1：预热平衡阶段</h2>")
    A("<p>本问取附录 2 的常数热物性，扩散系数仍随含水率变化，是模型链中的最小闭环，"
      "用于检验方程与边界实现的正确性。</p>")
    A("<p>图 1 给出四个时刻的径向分布。温度由表面向中心推进，中心始终滞后；"
      "含水率的下降集中在表层，中心在 1800&nbsp;s 内不变。"
      "这与第 1.2 节的量级判断一致：热量那边 \\(Fo=\\alpha t/R_0^2=0.76\\)，"
      "温度场已走完一轮瞬态；水分那边 \\(Fo_D=Dt/R_0^2=0.022\\)，仅处于起始阶段。</p>")
    A(figure("fig1_p1_profile", "图 1&nbsp;&nbsp;问题 1 的温度与干基含水率径向分布"))
    A("<p>1800&nbsp;s 时中心温度 33.5755&nbsp;℃、表面 36.7856&nbsp;℃，"
      "中心与表面温差 3.21&nbsp;K，而与烘房空气（此时 41.513&nbsp;℃）仍有明显差距，"
      "说明内部导热梯度不可忽略。含水率方面，\\(r\\le0.5\\)&nbsp;cm 处在四位小数下无变化，"
      "变化集中在距表面约 5&nbsp;mm 的薄层内，表面降至 1.5102&nbsp;kg/kg。</p>")
    A(table_html("problem_a_table_01_p1_temperature_v01", "1&nbsp;&nbsp;预热阶段药材温度（单位：℃）", "时间 / s"))
    A(table_html("problem_a_table_02_p1_moisture_v01", "2&nbsp;&nbsp;预热阶段药材干基含水率（单位：kg/kg）", "时间 / s"))

    # ---------------- 7 问题 2 ----------------
    A("<h2>7&nbsp;&nbsp;问题 2：变物性完整烘干过程</h2>")
    A("<p>本问改用附录 3 的物性关系，\\(\\rho\\)、\\(c_p\\)、\\(k\\) 成为含水率的函数，"
      "\\(D\\) 同时依赖含水率与温度，方程由拟线性转为完全非线性。"
      "预热平衡段与恒温干燥段的差别体现在边界条件上：0~14400&nbsp;s 直接采用附件 1 的实测值，"
      "其后按末次观测值（50.165&nbsp;℃、0.04986&nbsp;kg/kg）保持恒定。"
      "这样两段之间自然连续，无需人为设定切换时刻。</p>")
    A("<p>3&nbsp;h 时温度场已接近均匀，中心 49.8495&nbsp;℃ 与表面 49.9664&nbsp;℃ "
      "相差仅 0.12&nbsp;K，与烘房温度一致，说明预热平衡已经完成；"
      "含水率仍保持明显径向梯度，中心 1.7662&nbsp;kg/kg、表面 1.0081&nbsp;kg/kg（图 2）。</p>")
    A(figure("fig2_p2_profile", "图 2&nbsp;&nbsp;问题 2 的温度与干基含水率径向分布"))
    A("<p>与问题 1 相比，同样时间内水分变化剧烈得多（中心由 2.55 降到 1.77，"
      "而问题 1 的 30&nbsp;min 内中心毫无变化）。原因有两个："
      "温度升到 50&nbsp;℃ 后 \\(e^{-3850/T_K}\\) 放大，扩散加快；"
      "附录 3 的 \\(D\\) 随含水率下降的衰减速度明显慢于附录 2，"
      "从高含水率到低含水率，附录 2 的 \\(D\\) 下降约 265 倍，附录 3 只下降约 17 倍。</p>")
    A(table_html("problem_a_table_03_p2_temperature_v01", "3&nbsp;&nbsp;3 h 内药材温度（单位：℃）", "时间 / h"))
    A(table_html("problem_a_table_04_p2_moisture_v01", "4&nbsp;&nbsp;3 h 内药材干基含水率（单位：kg/kg）", "时间 / h"))

    # ---------------- 8 问题 3 ----------------
    A("<h2>8&nbsp;&nbsp;问题 3：固定半径下的烘干时长</h2>")
    A("<p>在同一模型上持续推进，直到全场含水率低于 0.15&nbsp;kg/kg。结果为 "
      "\\(t_3=57.21\\)&nbsp;h（2.38 天）。</p>")
    A("<p>过程呈现明显的长尾：中心含水率由 2.55 降到 0.30 只用了 18&nbsp;h，"
      "剩下的 0.15 又用了 39&nbsp;h。原因在 \\(D_{2,3}\\) 的 \\(e^{-0.45/C}\\) 项，"
      "含水率越低衰减越剧烈，\\(C\\) 由 1 降到 0.15 时该项下降十余倍，扩散接近停滞。"
      "表面在 12.6&nbsp;h 就已降到 0.15 以下，中心则一直拖到最后。</p>")
    A(figure("fig3_p3", "图 3&nbsp;&nbsp;问题 3：中心与表面含水率演化（左）与各时刻径向剖面（右）"))
    A(table_html("problem_a_table_05_p3_moisture_v01", "5&nbsp;&nbsp;固定半径下各时刻的干基含水率（单位：kg/kg）", "时间 / h"))

    # ---------------- 9 问题 4 ----------------
    A("<h2>9&nbsp;&nbsp;问题 4：考虑收缩的烘干时长</h2>")
    A("<p>本问改用附录 4 的物性关系，半径按附件 2 的实测序列由 2.000&nbsp;cm "
      "收缩到 1.198&nbsp;cm，计算域随之缩小。按第 4.3 节的物质坐标处理，得 "
      "\\(t_4=50.86\\)&nbsp;h（2.12 天），\\(R(t_4)=1.200\\)&nbsp;cm。</p>")
    A("<p>表 6 中各列按当前时刻到药材中心的距离给出，最后一列是当前表面（图 4）。"
      "由于半径在 3.64&nbsp;h 已缩到 1.5&nbsp;cm 以下，1.5&nbsp;cm 一列在该时刻之后"
      "落到药材之外，按题目“药材内部水分浓度”的表述留空。"
      "若改按材料点标注，表头应写成各点的初始位置，两套口径的中间几列数值不同，不宜混用。</p>")
    A(figure("fig4_p4", "图 4&nbsp;&nbsp;问题 4：半径路径与附件 2 实测值的比较（左）、中心与表面含水率演化（右）"))
    A("<p>收缩的影响需要与物性变化分开考察。问题 3 与问题 4 同时改变了物性公式和几何，"
      "两者之差不能直接解释为收缩效应。在同一物性（附录 4）下作对照："
      "无收缩 129.14&nbsp;h，含收缩 50.86&nbsp;h，即收缩把烘干时间缩短到 0.39 倍，"
      "提速 2.54 倍。收缩使扩散路径由 2.0&nbsp;cm 降到 1.198&nbsp;cm，"
      "特征时间按 \\((2/1.198)^2=2.79\\) 倍缩短，与实测提速倍数吻合。</p>")
    A("<p>这一对照也解释了为什么问题 4 必须做动边界：若沿用固定半径，"
      "附录 4 的物性会给出 5.4 天，与题干“2~3 天”直接矛盾。</p>")
    A(table_html("problem_a_table_06_p4_moisture_v01", "6&nbsp;&nbsp;考虑收缩时各时刻的干基含水率（单位：kg/kg）", "时间 / h"))

    # ---------------- 10 检验与灵敏度 ----------------
    A("<h2>10&nbsp;&nbsp;模型检验与灵敏度分析</h2>")
    A("<h3>10.1&nbsp;&nbsp;网格与时间步收敛</h3>")
    A("<p>以问题 1 在 1800&nbsp;s 的解为对象，同时对空间和时间加密。"
      "相邻两级之间温度的最大偏差依次为 \\(4.90\\times10^{-4}\\)、\\(2.72\\times10^{-4}\\)、"
      "\\(1.43\\times10^{-4}\\)、\\(7.32\\times10^{-5}\\)、\\(3.70\\times10^{-5}\\)&nbsp;K，"
      "比值稳定在 0.5 附近；温度收敛阶估计为 0.85、0.93、0.97、0.98，逐级趋近一阶，"
      "与“一阶时间 + 一阶空间”的格式相符。"
      "生产设置（640 层、0.1&nbsp;s）与参考设置（640 层、0.03125&nbsp;s）的偏差为 "
      "\\(8.2\\times10^{-5}\\)&nbsp;K 与 \\(6.0\\times10^{-6}\\)&nbsp;kg/kg，"
      "远低于四位小数要求（图 5a）。</p>")
    A("<p>问题 3 的烘干时长对空间网格的收敛过程为：\\(N=20\\) 时 56.23&nbsp;h，"
      "40 时 56.76，80 时 57.02，160 时 57.14，320 时 57.19，640 时 57.21。"
      "相邻差值依次为 0.53、0.26、0.12、0.05&nbsp;h，每加密一倍减半。"
      "这组数据说明 \\(N=20\\) 的结果尚未进入收敛区间，也说明生产网格已经足够。"
      "需要指出，烘干时长本身存在约 0.3&nbsp;h 的数值不确定度："
      "结束前中心含水率每小时只降约 0.001&nbsp;kg/kg，含水率 \\(10^{-4}\\) 的差异"
      "即对应约 0.1&nbsp;h，因此该时间报至 0.1&nbsp;h 量级即可。</p>")

    A("<h3>10.2&nbsp;&nbsp;守恒性与解析解对比</h3>")
    A("<p>离散格式的守恒性可逐项核验。以初始状态为基准，内部焓的变化应等于"
      "表面热通量的时间积分，干物质含水量的变化应等于表面传质通量的时间积分。"
      "实测相对残差为能量 \\(2.7\\times10^{-12}\\)、水分 \\(3.4\\times10^{-13}\\)，"
      "说明通量在界面上严格抵消。</p>")
    A("<p>取环境温度恒为 50&nbsp;℃、物性为常数，模型退化为经典的圆柱非稳态导热问题，"
      "其分离变量级数解可作基准。数值解与之的最大偏差在细网格上为 "
      "\\(2.5\\times10^{-4}\\)&nbsp;K，在生产网格上为 \\(3.9\\times10^{-4}\\)&nbsp;K，"
      "而整个过程温升为 22&nbsp;K，相对误差约 \\(10^{-5}\\)。"
      "这一项同时确认了空间离散与时间步长均已足够。</p>")

    A("<h3>10.3&nbsp;&nbsp;界面系数平均方式的收敛对照</h3>")
    A("<p>有限体积法界面上的传导率可以取算术平均，也可以取调和平均。"
      "两种规则都是相容格式，网格加密后必须收敛到同一结果；"
      "但在强非线性区（表面含水率已很低、\\(D\\) 掉到 \\(10^{-12}\\) 量级）"
      "粗网格上的差异很大，容易把网格误差误读为物理效应。"
      "为此对“平均方式 × 网格层数 × 传质口径”做了完整对照，结果见表 7。</p>")
    A("<table><caption>表 7&nbsp;&nbsp;界面系数平均方式与网格层数的收敛对照"
      "（问题 3 烘干时长，单位 h）</caption><thead><tr><th>网格层数</th>"
      "<th>\\(km{=}1\\) 算术</th><th>\\(km{=}1\\) 调和</th>"
      "<th>\\(km{=}820\\) 算术</th><th>\\(km{=}820\\) 调和</th></tr></thead><tbody>")
    for row in [("320", "57.190", "57.617", "53.140", "174.75"),
                ("640", "57.211", "57.290", "53.200", "106.42"),
                ("1280", "57.218", "57.236", "53.227", "75.06"),
                ("2560", "57.221", "57.225", "53.240", "61.55")]:
        A("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    A("</tbody></table>")
    A("<p>\\(km=1\\) 时两种平均在 2560 层收敛到同一个值 57.22&nbsp;h，"
      "本文生产用的算术平均在 640 层即为 57.21&nbsp;h，已落在收敛值上，偏差 0.02%。"
      "\\(km=820\\) 的调和平均在 320 层给出 174.75&nbsp;h，随网格加密单调下降到 "
      "61.55&nbsp;h，朝算术平均的 53.24&nbsp;h 靠拢，属未收敛的中间结果。"
      "这组对照说明：比较两种离散格式之前必须确认两边都已收敛，"
      "否则网格误差会被当作物理效应；本文的传质口径灵敏度必须在收敛口径下计算。</p>")

    A("<h3>10.4&nbsp;&nbsp;传质口径灵敏度</h3>")
    A("<p>题目给出的含水率是干基含水率（相对干物料），而空气水分浓度是绝对湿度"
      "（相对干空气），两者基准不同。边界式 "
      "\\(-D\\,\\partial C/\\partial r=k_m[C(R,t)-C_\\infty]\\) 相当于把空气侧的湿度"
      "按与药材含水率同一口径处理，是本题可用的最小假设；"
      "严格换算需要吸附等温线与干物质密度，题目未给。"
      "为判断该假设的影响，引入无量纲系数 \\(\\kappa\\)，"
      "令有效传质系数为 \\(\\kappa h_m\\)，结果见表 8 与图 5b。</p>")
    A("<table><caption>表 8&nbsp;&nbsp;传质口径灵敏度（问题 3 烘干时长）</caption>"
      "<thead><tr><th>\\(\\kappa\\)</th><th>0.1</th><th>1（基线）</th>"
      "<th>10</th><th>820</th></tr></thead><tbody>")
    for lab, vals in [("表面降到 0.15 的时刻 / h", ["110.1", "12.6", "2.5", "0.0"]),
                      ("整体降到 0.15 的时刻 / h", ["144.5", "57.2", "53.2", "53.2"]),
                      ("24 h 时中心含水率 / (kg/kg)", ["1.37", "0.24", "0.21", "0.21"])]:
        A(f"<tr><td>{lab}</td>" + "".join(f"<td>{v}</td>" for v in vals) + "</tr>")
    A("</tbody></table>")
    A("<p>把口径放大到内扩散控制极限，烘干时长只由 57.2&nbsp;h 降到 53.2&nbsp;h"
      "（−7%），且 \\(\\kappa\\ge10\\) 后已经饱和，说明内部扩散始终是主控环节，"
      "外边界阻力并非瓶颈。反过来，口径缩小到 0.1 时外部传质成为瓶颈，"
      "24&nbsp;h 时中心含水率仍有 1.37&nbsp;kg/kg，整体需要 144.5&nbsp;h，"
      "与题干区间矛盾。因此题目给定的 \\(h_m=8\\times10^{-7}\\)&nbsp;m/s "
      "落在唯一能与“2~3 天”自洽的区间内，模型对口径放大的方向不敏感。</p>")

    A("<h3>10.5&nbsp;&nbsp;蒸发潜热的量级审计</h3>")
    A("<p>主模型未向能量方程叠加蒸发潜热项。这一简化是否成立，可作量级审计："
      "在 1800&nbsp;s，表面含水率 1.5102&nbsp;kg/kg、空气水分浓度 0.0331&nbsp;kg/kg，"
      "按题给传质系数得界面通量（以含水率口径计）\\(1.18\\times10^{-6}\\)&nbsp;kg/(kg·s)；"
      "若分别按表观密度 820&nbsp;kg/m³ 和干物质密度 231&nbsp;kg/m³ 折算为质量通量，"
      "再乘以水的汽化潜热 \\(2.257\\times10^{6}\\)&nbsp;J/kg，"
      "得潜热汇约 2187&nbsp;W/m² 与 616&nbsp;W/m²；"
      "同一时刻对流供热为 \\(h(T_\\infty-T_s)=118\\)&nbsp;W/m²。"
      "潜热需求是对流供热的 5.2~18.5 倍，取决于密度口径。</p>")
    A("<p>这说明题给的热、质边界是分别标定的等效闭合，不能与潜热项机械拼合："
      "一旦叠加，表面会在远低于空气温度处达到能量平衡，"
      "模型将由内部扩散控制转为供热控制，与题干给出的时间尺度不符。"
      "严格的潜热耦合需要干物质密度、气固平衡含水率关系与有效汽化潜热，"
      "题目均未提供，故本文将其列为扩展模型。</p>")

    A("<h3>10.6&nbsp;&nbsp;两阶段切换点与收缩效应的分离</h3>")
    A("<p>预热平衡段与恒温干燥段的划分方式可作检验。"
      "把切换点显式取在 1.5&nbsp;h、2&nbsp;h、4&nbsp;h 三种位置重新计算，"
      "烘干时长均为 57.58&nbsp;h，与默认的连续边界处理（57.21&nbsp;h）相差 0.6%，"
      "说明切换判据不敏感。</p>")
    A("<p>收缩与物性变化的分离见第 9 节：在附录 4 物性下，无收缩为 129.14&nbsp;h，"
      "含收缩为 50.86&nbsp;h，收缩使时间缩短约 61%；"
      "而问题 3 到问题 4 的净变化仅 −11%，因为物性变化使时间延长了 2.26 倍，"
      "与收缩的缩短作用部分抵消。把两者混在一起讨论会严重低估收缩的作用。</p>")
    A(figure("fig5_verification", "图 5&nbsp;&nbsp;模型检验：(a) 网格与时间步收敛；"
             "(b) 传质口径灵敏度；(c) 界面系数平均方式的收敛对照"))

    # ---------------- 11 评价 ----------------
    A("<h2>11&nbsp;&nbsp;模型评价与改进方向</h2>")
    A("<h3>11.1&nbsp;&nbsp;模型优点</h3>")
    A("<p>模型直接由守恒定律导出，各项物理含义明确；"
      "有限体积离散在柱坐标下保持守恒，中心奇异性自然消除，"
      "且同一套代码通过替换物性函数即可覆盖四个问题；"
      "问题 4 采用物质坐标，避免动网格重构，半径缩小时节点值不发生虚假跳变；"
      "模型对网格、时间步、界面平均方式与两阶段切换点均作了收敛或敏感性检验，"
      "结论不依赖离散细节。</p>")
    A("<h3>11.2&nbsp;&nbsp;模型局限</h3>")
    A("<p>第一，恒温干燥段的空气温湿度由附件 1 的末值外推，附件 1 只覆盖 4&nbsp;h，"
      "这是模型最主要的外部不确定性来源；改用平台段均值只使烘干时长变化 0.6%，"
      "但若实际工艺另有设定值则需重算。"
      "第二，模型未显式耦合蒸发潜热，理由见第 10.5 节，"
      "这限制了它在供热受限工况下的适用性。"
      "第三，水分迁移简化为单一有效扩散，未区分液态迁移与蒸汽扩散，"
      "也未考虑表面结壳与各向异性。"
      "第四，附件 2 的半径在约 20&nbsp;h 后基本停止收缩，而含水率要到约 57&nbsp;h 才达标，"
      "实测收缩快于失水，说明该序列由外部标定，不宜反过来作为失水的验证量。"
      "第五，问题 2 结果文件的时间范围在题目中存在两种读法（前 3&nbsp;h 或整个烘干过程），"
      "本文同时提供两份结果。</p>")

    # ---------------- 12 结论 ----------------
    A("<h2>12&nbsp;&nbsp;结论</h2>")
    A("<p>本文建立了圆柱药材热风干燥的一维径向热湿传递模型，"
      "并用守恒有限体积法求解四个问题。</p><ol>")
    for t in [
        "预热 1800&nbsp;s 时中心与表面温度分别为 33.5755&nbsp;℃ 与 36.7856&nbsp;℃，"
        "干基含水率为 2.5500 与 1.5102&nbsp;kg/kg；水分变化集中在距表面约 5&nbsp;mm 的薄层内。",
        "采用附录 3 变物性后，3&nbsp;h 时温度场接近均匀（中心 49.8495&nbsp;℃、"
        "表面 49.9664&nbsp;℃），含水率仍保持径向梯度（中心 1.7662、表面 1.0081&nbsp;kg/kg）。",
        "固定半径下烘干时长为 57.21&nbsp;h；网格加密到 2560 层后收敛到 57.22&nbsp;h，"
        "算术与调和两种界面平均方式给出同一结果。",
        "计入附件 2 的收缩路径后烘干时长为 50.86&nbsp;h，结束时半径约 1.200&nbsp;cm；"
        "在同一物性下，收缩使烘干时间缩短约 61%，是决定结果量级的关键因素。",
    ]:
        A(f"<li>{t}</li>")
    A("</ol>")

    # ---------------- 参考文献 ----------------
    A('<h2>参考文献</h2><div class="ref">')
    for i, s in enumerate([
        "Incropera F P, DeWitt D P, Bergman T L, et al. Fundamentals of Heat and Mass "
        "Transfer. 7th ed. Hoboken: John Wiley &amp; Sons, 2011.",
        "Carslaw H S, Jaeger J C. Conduction of Heat in Solids. 2nd ed. Oxford: "
        "Clarendon Press, 1959.",
        "Patankar S V. Numerical Heat Transfer and Fluid Flow. New York: Hemisphere "
        "Publishing, 1980.",
        "Crank J. The Mathematics of Diffusion. 2nd ed. Oxford: Clarendon Press, 1975.",
    ], 1):
        A(f"<p>[{i}]&nbsp;&nbsp;{s}</p>")
    A("</div>")

    # ---------------- 附录 ----------------
    A("<h2>附录&nbsp;&nbsp;程序与结果文件说明</h2>")
    A("<p>全部计算由 Python 完成，代码与结果文件的对应关系如下：</p><ul>")
    for t in ["<code>src/config.py</code>：几何与附录 2 参数、数值配置",
              "<code>src/preprocess.py</code>：附件 1、2 的质量检查与分段线性插值",
              "<code>src/fv.py</code>：节点中心有限体积求解器，支持动边界与两种界面平均方式",
              "<code>src/props.py</code>：附录 3、4 的经验关系",
              "<code>src/run_p1.py</code>、<code>src/run_p234.py</code>：四个问题的主程序",
              "<code>src/verify_p1.py</code>：收敛性、守恒性与解析解校验",
              "<code>src/convergence_face_avg.py</code>、"
              "<code>src/convergence_extreme.py</code>：界面平均方式的收敛对照",
              "<code>src/sens_km.py</code>：传质口径灵敏度",
              "<code>output/result1.xlsx</code> ~ <code>result4.xlsx</code>：题目要求的结果文件",
              "<code>logs/</code>：各次检验的原始数据（JSON）"]:
        A(f"<li>{t}</li>")
    A("</ul>")
    A("<p>程序只读取题目附件，不在运行过程中修改原始数据；随机性不参与计算，结果可完全复现。</p>")
    A("</body></html>")

    html = "\n".join(H)
    (PAPER / "paper.html").write_text(html, encoding="utf-8")
    print("HTML 已生成：", PAPER / "paper.html", f"({len(html)/1024:.0f} KB)")

    exe = next((c for c in CHROME if Path(c).exists()), None)
    if exe is None:
        print("未找到浏览器，跳过 PDF 生成")
        return
    pdf = PAPER / "problem_a_paper_cc_v01.pdf"
    if pdf.exists():
        pdf.unlink()
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", "--virtual-time-budget=30000",
           f"--print-to-pdf={pdf}", (PAPER / "paper.html").as_uri()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    print("浏览器返回码:", r.returncode)
    if r.stderr:
        tail = [l for l in r.stderr.splitlines() if l.strip()][-5:]
        print("stderr:", "\n".join(tail))
    print("PDF 已生成：" if pdf.exists() else "PDF 未生成：", pdf,
          f"({pdf.stat().st_size/1048576:.2f} MB)" if pdf.exists() else "")
    if pdf.exists():
        add_page_numbers(pdf)


def add_page_numbers(pdf):
    """给 PDF 加页脚页码（浏览器不打印时 Chrome 的页眉页脚已关闭）。"""
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "STSong"
    try:
        pdfmetrics.registerFont(TTFont(font_name, r"C:\Windows\Fonts\simsun.ttc"))
    except Exception:
        font_name = "Helvetica"

    reader = PdfReader(str(pdf))
    writer = PdfWriter()
    total = len(reader.pages)
    for i, page in enumerate(reader.pages, 1):
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont(font_name, 9)
        c.drawCentredString(A4[0] / 2, 32, f"{i} / {total}")
        c.save()
        buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])
        writer.add_page(page)
    tmp = pdf.with_suffix(".tmp.pdf")
    with open(tmp, "wb") as fh:
        writer.write(fh)
    tmp.replace(pdf)
    print("已加页码，共", total, "页")


if __name__ == "__main__":
    main()
