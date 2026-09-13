"""Create Chinese publication figures for the 2026 CUMCM Problem A paper."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
import numpy as np
import pandas as pd


ROOT = Path(".")
RESULTS = ROOT / "outputs" / "results"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
AIR_FILE = ROOT / "data" / "raw" / "problem_a_raw_attachment_1_v01.xlsx"
RADIUS_FILE = ROOT / "data" / "raw" / "problem_a_raw_attachment_2_v01.xlsx"
LATENT_AUDIT_FILE = TABLES / "problem_a_table_07_latent_heat_audit_v01.csv"


def select_chinese_font() -> str:
    """Choose an installed CJK font by family name, without OS-specific paths."""

    available = {item.name for item in font_manager.fontManager.ttflist}
    candidates = [
        "Arial Unicode MS",
        "Microsoft YaHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Heiti TC",
        "SimHei",
        "WenQuanYi Micro Hei",
    ]
    return next((name for name in candidates if name in available), "DejaVu Sans")


CHINESE_FONT = select_chinese_font()
FONT = FontProperties(family=CHINESE_FONT, size=7.6)
FONT_SMALL = FontProperties(family=CHINESE_FONT, size=6.8)
FONT_TITLE = FontProperties(family=CHINESE_FONT, size=8.2, weight="bold")

BLUE = "#0F4D92"
BLUE_MID = "#7884B4"
BLUE_SOFT = "#B4C0E4"
ORANGE = "#D55E00"
RED = "#B64342"
TEAL = "#42949E"
GREEN = "#2E9E44"
GRAY = "#606060"
LIGHT_GRAY = "#CFCECE"
WARM_SHADE = "#F7E6DF"
COOL_SHADE = "#E8F0F7"
TIME_COLORS = [LIGHT_GRAY, "#AFC2D7", "#5E89B5", BLUE]


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                CHINESE_FONT,
                "Arial",
                "DejaVu Sans",
                "Liberation Sans",
            ],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 7.6,
            "axes.unicode_minus": False,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "lines.linewidth": 1.5,
            "savefig.transparent": False,
            "savefig.facecolor": "white",
            "mathtext.fontset": "stix",
        }
    )


def polish_axis(axis: plt.Axes) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["bottom", "left"]].set_color("#454545")
    axis.tick_params(labelsize=7, length=3, color="#454545")
    axis.grid(axis="y", color="#D9D9D9", linewidth=0.45, alpha=0.55, zorder=0)


def add_panel_label(axis: plt.Axes, label: str) -> None:
    axis.text(
        -0.13,
        1.04,
        label,
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


def read_wide(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def radii_from_columns(frame: pd.DataFrame) -> np.ndarray:
    return np.asarray(
        [float(column.removeprefix("r_").removesuffix("_cm")) for column in frame.columns[1:]]
    )


def nearest_row(frame: pd.DataFrame, time_s: float) -> pd.Series:
    index = int(np.argmin(np.abs(frame["time_s"].to_numpy(float) - time_s)))
    return frame.iloc[index]


def figure_inputs() -> None:
    air = pd.read_excel(AIR_FILE)
    radius = pd.read_excel(RADIUS_FILE)
    fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.25), constrained_layout=True)
    air_time_h = air.iloc[:, 0] / 3600
    radius_time_h = radius.iloc[:, 0] / 3600
    # Temperature alone flattens earlier, but both recorded boundary variables
    # enter their narrow terminal bands only at about 2.5 h.
    axes[0].axvspan(0, 2.5, color=WARM_SHADE, alpha=0.75, zorder=0)
    axes[0].axvspan(2.5, 4, color=COOL_SHADE, alpha=0.75, zorder=0)
    axes[1].axvspan(0, 2.5, color=WARM_SHADE, alpha=0.75, zorder=0)
    axes[1].axvspan(2.5, 4, color=COOL_SHADE, alpha=0.75, zorder=0)
    axes[0].plot(air_time_h, air.iloc[:, 1], color=RED, zorder=2)
    axes[0].scatter(air_time_h[::20], air.iloc[::20, 1], color=RED, s=5, zorder=3)
    axes[1].plot(air_time_h, air.iloc[:, 2], color=BLUE, zorder=2)
    axes[1].scatter(air_time_h[::20], air.iloc[::20, 2], color=BLUE, s=5, zorder=3)
    axes[2].plot(radius_time_h, radius.iloc[:, 1], color=TEAL, zorder=2)
    axes[2].scatter(radius_time_h[::12], radius.iloc[::12, 1], color=TEAL, s=5, zorder=3)
    labels = [
        ("烘房温度", r"温度/$^{\circ}\mathrm{C}$"),
        ("烘房水分浓度", r"水分浓度/$\mathrm{kg/kg}$"),
        ("药材半径", r"半径/$\mathrm{cm}$"),
    ]
    for panel, axis, (title, ylabel) in zip("abc", axes, labels, strict=True):
        axis.set_title(title, fontproperties=FONT_TITLE)
        axis.set_xlabel(r"时间/$\mathrm{h}$", fontproperties=FONT)
        axis.set_ylabel(ylabel, fontproperties=FONT)
        add_panel_label(axis, panel)
        polish_axis(axis)
    axes[0].text(0.19, 0.10, "升温—过渡段", transform=axes[0].transAxes, color=GRAY, fontproperties=FONT_SMALL)
    axes[0].text(0.76, 0.10, "超稳段", transform=axes[0].transAxes, color=GRAY, fontproperties=FONT_SMALL)
    axes[2].axvline(4, color=GRAY, linewidth=0.8, linestyle="--")
    axes[2].annotate(
        "4 h：炉况序列结束",
        xy=(4, float(np.interp(4 * 3600, radius.iloc[:, 0], radius.iloc[:, 1]))),
        xytext=(14, 1.72),
        textcoords="data",
        arrowprops={"arrowstyle": "->", "lw": 0.7, "color": GRAY},
        ha="left",
        va="center",
        color=GRAY,
        fontproperties=FONT_SMALL,
    )
    save_figure(fig, "problem_a_figure_04_boundary_and_radius_v03")


def plot_profile_pair(
    temperature_name: str,
    moisture_name: str,
    times_s: list[int],
    labels: list[str],
    stem: str,
    title_suffix: str,
) -> None:
    temperature = read_wide(temperature_name)
    moisture = read_wide(moisture_name)
    radii = radii_from_columns(temperature)
    colors = TIME_COLORS[-len(times_s) :]
    styles = [":", "--", "-.", "-"]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.6), constrained_layout=True)
    for time_s, label, color, style in zip(
        times_s, labels, colors[: len(times_s)], styles[: len(times_s)], strict=True
    ):
        temperature_values = (
            np.full_like(radii, 28.0)
            if time_s == 0
            else nearest_row(temperature, time_s).iloc[1:].to_numpy(float)
        )
        moisture_values = (
            np.full_like(radii, 2.55)
            if time_s == 0
            else nearest_row(moisture, time_s).iloc[1:].to_numpy(float)
        )
        axes[0].plot(
            radii,
            temperature_values,
            color=color,
            linestyle=style,
            label=label,
        )
        axes[1].plot(
            radii,
            moisture_values,
            color=color,
            linestyle=style,
            label=label,
        )
        axes[0].scatter(radii[-1], temperature_values[-1], color=color, s=8, zorder=3)
        axes[1].scatter(radii[-1], moisture_values[-1], color=color, s=8, zorder=3)
    axes[0].set_title(f"{title_suffix}温度剖面", fontproperties=FONT_TITLE)
    axes[0].set_ylabel(r"温度/$^{\circ}\mathrm{C}$", fontproperties=FONT)
    axes[1].set_title(f"{title_suffix}水分浓度剖面", fontproperties=FONT_TITLE)
    axes[1].set_ylabel(r"水分浓度/$\mathrm{kg/kg}$", fontproperties=FONT)
    for panel, axis in zip("ab", axes, strict=True):
        axis.set_xlabel(r"到药材中心的距离/$\mathrm{cm}$", fontproperties=FONT)
        add_panel_label(axis, panel)
        polish_axis(axis)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.04),
        ncol=len(labels),
        prop=FONT_SMALL,
    )
    save_figure(fig, stem)


def figure_drying_endpoint() -> None:
    q3 = read_wide("problem_a_result_07_q3_moisture_v01.csv")
    q4 = read_wide("problem_a_result_08_q4_moisture_v01.csv")
    radius = pd.read_excel(RADIUS_FILE)
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.85), constrained_layout=True)
    cmap = plt.get_cmap("YlGnBu_r")
    shared_image = None
    for panel, axis, frame, title in [
        ("a", axes[0], q3, "问题3：固定半径"),
        ("b", axes[1], q4, "问题4：收缩半径"),
    ]:
        sampled = frame.iloc[::5].copy()
        time_h = sampled["time_s"].to_numpy(float) / 3600.0
        value_columns = [column for column in sampled.columns if column.startswith("r_")]
        radii_cm = np.asarray(
            [float(column.removeprefix("r_").removesuffix("_cm")) for column in value_columns]
        )
        values = sampled[value_columns].to_numpy(float).T
        shared_image = axis.pcolormesh(
            time_h,
            radii_cm,
            values,
            shading="auto",
            cmap=cmap,
            vmin=0.05,
            vmax=2.55,
            rasterized=True,
        )
        axis.contour(
            time_h,
            radii_cm,
            values,
            levels=[0.15],
            colors=[RED],
            linewidths=1.25,
        )
        end_h = float(frame["time_s"].iloc[-1] / 3600.0)
        axis.scatter(end_h, 0.0, s=20, color=RED, edgecolor="white", linewidth=0.5, zorder=5)
        axis.annotate(
            f"中心达标 {end_h:.2f} h",
            xy=(end_h, 0.0),
            xytext=(-72, 18),
            textcoords="offset points",
            arrowprops={"arrowstyle": "->", "lw": 0.7, "color": RED},
            color=RED,
            fontproperties=FONT_SMALL,
        )
        axis.set_title(title, fontproperties=FONT_TITLE)
        axis.set_xlabel(r"时间/$\mathrm{h}$", fontproperties=FONT)
        axis.set_ylabel(r"到中心距离/$\mathrm{cm}$", fontproperties=FONT)
        axis.grid(False)
        add_panel_label(axis, panel)
        polish_axis(axis)
        axis.grid(False)
    q4_time_h = q4["time_s"].to_numpy(float) / 3600.0
    q4_radius_cm = np.interp(
        q4["time_s"].to_numpy(float),
        radius.iloc[:, 0].to_numpy(float),
        radius.iloc[:, 1].to_numpy(float),
    )
    axes[1].fill_between(
        q4_time_h,
        q4_radius_cm,
        2.08,
        color="white",
        zorder=3,
    )
    axes[1].plot(q4_time_h, q4_radius_cm, color="white", linewidth=2.4, zorder=4)
    axes[1].plot(q4_time_h, q4_radius_cm, color="#17324D", linewidth=0.9, zorder=5, label="$R(t)$")
    axes[1].legend(loc="upper right", prop=FONT_SMALL)
    colorbar = fig.colorbar(shared_image, ax=axes, location="right", shrink=0.94, pad=0.02)
    colorbar.set_label(r"水分浓度/$\mathrm{kg/kg}$", fontproperties=FONT)
    colorbar.ax.tick_params(labelsize=6.5)
    save_figure(fig, "problem_a_figure_07_drying_endpoint_v03")


def figure_counterfactual() -> None:
    frame = pd.read_csv(TABLES / "problem_a_table_05_counterfactual_comparison_v01.csv")
    fixed = frame[frame["radius_path"] == "fixed 2 cm"]["drying_time_h"].to_numpy()
    shrinking = frame[frame["radius_path"] == "measured shrinkage"]["drying_time_h"].to_numpy()
    x = np.arange(2)
    width = 0.34
    fig, axis = plt.subplots(figsize=(4.8, 3.0), constrained_layout=True)
    bars_fixed = axis.bar(
        x - width / 2,
        fixed,
        width,
        color=BLUE_SOFT,
        edgecolor=BLUE,
        linewidth=0.9,
        label=r"固定半径 $R=2\,\mathrm{cm}$",
    )
    bars_shrink = axis.bar(
        x + width / 2,
        shrinking,
        width,
        color=ORANGE,
        edgecolor="#7A3100",
        linewidth=0.9,
        hatch="///",
        label="附件2收缩路径",
    )
    axis.bar_label(bars_fixed, fmt="%.1f", padding=2, fontsize=8)
    axis.bar_label(bars_shrink, fmt="%.1f", padding=2, fontsize=8)
    axis.set_xticks(x, ["附录3物性关联式", "附录4物性关联式"], fontproperties=FONT)
    axis.set_ylabel(r"烘干时长/$\mathrm{h}$", fontproperties=FONT)
    axis.set_title("同物性参数下的收缩反事实", fontproperties=FONT_TITLE)
    axis.legend(prop=FONT_SMALL, frameon=False)
    reductions = 100 * (fixed - shrinking) / fixed
    for position, reduction, top in zip(x, reductions, fixed, strict=True):
        axis.text(
            position,
            top + 5,
            rf"$-{reduction:.1f}\%$",
            ha="center",
            va="bottom",
            fontsize=7.2,
            color=GRAY,
        )
    axis.set_ylim(0, max(fixed) * 1.18)
    polish_axis(axis)
    save_figure(fig, "problem_a_figure_08_counterfactual_v03")


def figure_sensitivity() -> None:
    frame = pd.read_csv(TABLES / "problem_a_table_06_sensitivity_v01.csv").set_index("case")
    regular_cases = [
        "h_minus_20pct",
        "h_plus_20pct",
        "hm_minus_20pct",
        "hm_plus_20pct",
        "terminal_temperature_minus_2c",
        "terminal_temperature_plus_2c",
    ]
    regular_labels = [r"$h$ -20%", r"$h$ +20%", r"$h_m$ -20%", r"$h_m$ +20%", r"$T_\infty$ -2℃", r"$T_\infty$ +2℃"]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.9), constrained_layout=True)

    y = np.arange(len(regular_cases))
    q3_regular = frame.loc[regular_cases, "q3_change_percent"].to_numpy(float)
    q4_regular = frame.loc[regular_cases, "q4_change_percent"].to_numpy(float)
    bar_height = 0.30
    for values, offset, color, hatch, label in [
        (q3_regular, -bar_height / 2, BLUE, None, "问题3"),
        (q4_regular, bar_height / 2, ORANGE, "///", "问题4"),
    ]:
        axes[0].barh(
            y + offset,
            values,
            height=bar_height,
            color=color,
            alpha=0.88,
            hatch=hatch,
            edgecolor=color,
            linewidth=0.6,
            label=label,
            zorder=2,
        )
    axes[0].axvline(0, color="#333333", linewidth=0.8)
    axes[0].set_yticks(y, regular_labels, fontproperties=FONT)
    axes[0].set_xlabel(r"烘干时长变化/$\%$", fontproperties=FONT)
    axes[0].set_title("常规参数扰动", fontproperties=FONT_TITLE)
    axes[0].invert_yaxis()
    axes[0].set_xlim(-7.5, 8.0)
    add_panel_label(axes[0], "a")
    polish_axis(axes[0])

    humid_cases = [
        "terminal_moisture_minus_20pct",
        "baseline",
        "terminal_moisture_plus_20pct",
    ]
    humid_labels = [
        r"$C_\infty-20\%$",
        r"基准 $C_\infty$",
        r"$C_\infty+20\%$",
    ]
    y_humid = np.arange(len(humid_cases))
    for column, offset, color, marker, label in [
        ("q3_drying_time_h", 0.11, BLUE, "o", "问题3"),
        ("q4_drying_time_h", -0.11, ORANGE, "s", "问题4"),
    ]:
        values = frame.loc[humid_cases, column].to_numpy(float)
        axes[1].plot(values, y_humid + offset, color=color, linewidth=1.1)
        axes[1].scatter(values, y_humid + offset, color=color, marker=marker, s=18, label=label, zorder=3)
        for value, y_value in zip(values, y_humid + offset, strict=True):
            axes[1].text(value + 2.2, y_value, f"{value:.1f}", va="center", fontsize=6.2, color=color)
    axes[1].set_yticks(y_humid, humid_labels, fontproperties=FONT)
    axes[1].set_xlabel(r"烘干时长/$\mathrm{h}$", fontproperties=FONT)
    axes[1].set_title("长期空气水分扰动", fontproperties=FONT_TITLE)
    axes[1].invert_yaxis()
    axes[1].set_xlim(40, 180)
    add_panel_label(axes[1], "b")
    polish_axis(axes[1])

    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.04),
        ncol=2,
        prop=FONT_SMALL,
    )
    save_figure(fig, "problem_a_figure_09_sensitivity_v03")


def figure_latent_heat_audit() -> None:
    frame = pd.read_csv(LATENT_AUDIT_FILE)
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.65), constrained_layout=True)
    time_h = frame["time_h"].to_numpy(float)

    axes[0].plot(
        time_h,
        frame["latent_heat_flux_demand_w_per_m2"],
        color=RED,
        marker="o",
        markersize=3,
        label=r"潜热需求 $q_{\ell}^{*}$",
    )
    axes[0].plot(
        time_h,
        frame["convective_heat_flux_w_per_m2"],
        color=BLUE,
        marker="s",
        markersize=3,
        label=r"对流供热 $q_h$",
    )
    axes[0].fill_between(
        time_h,
        frame["convective_heat_flux_w_per_m2"],
        frame["latent_heat_flux_demand_w_per_m2"],
        color=WARM_SHADE,
        alpha=0.9,
    )
    axes[0].set_yscale("log")
    axes[0].set_title("边界热流量级审计", fontproperties=FONT_TITLE)
    axes[0].set_xlabel(r"时间/$\mathrm{h}$", fontproperties=FONT)
    axes[0].set_ylabel(r"热流密度/$\mathrm{W\,m^{-2}}$", fontproperties=FONT)
    axes[0].legend(loc="lower right", prop=FONT_SMALL)
    add_panel_label(axes[0], "a")
    polish_axis(axes[0])

    available = frame["available_temperature_difference_k"].to_numpy(float)
    required = frame["required_temperature_difference_k"].to_numpy(float)
    axes[1].plot(time_h, required, color=RED, marker="o", markersize=3, label=r"所需 $\Delta T_{\ell}^{*}$")
    axes[1].plot(time_h, available, color=BLUE, marker="s", markersize=3, label=r"现有 $\Delta T$")
    axes[1].fill_between(time_h, available, required, color=WARM_SHADE, alpha=0.9)
    half_hour = int(np.argmin(np.abs(time_h - 0.5)))
    axes[1].annotate(
        rf"$0.5\,\mathrm{{h}}$：{required[half_hour] / available[half_hour]:.2f} 倍",
        xy=(time_h[half_hour], required[half_hour]),
        xytext=(0.93, 0.82),
        textcoords="axes fraction",
        ha="right",
        arrowprops={"arrowstyle": "->", "lw": 0.7, "color": GRAY},
        color=GRAY,
        fontproperties=FONT_SMALL,
    )
    axes[1].set_title("温差供需对照", fontproperties=FONT_TITLE)
    axes[1].set_xlabel(r"时间/$\mathrm{h}$", fontproperties=FONT)
    axes[1].set_ylabel(r"温差/$\mathrm{K}$", fontproperties=FONT)
    axes[1].legend(loc="lower right", prop=FONT_SMALL)
    add_panel_label(axes[1], "b")
    polish_axis(axes[1])
    save_figure(fig, "problem_a_figure_10_latent_heat_audit_v01")


def figure_reviewer_robustness() -> None:
    audit_path = RESULTS / "problem_a_result_17_reviewer_audit_v01.json"
    if not audit_path.exists():
        return
    import json

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.75), constrained_layout=True)

    teammate = audit["teammate_backward_euler_baseline"]
    bdf = audit["bdf_event_baseline"]
    labels = ["问题3", "问题4"]
    y = np.arange(2)
    be_values = np.array([teammate["question_3_h"], teammate["question_4_h"]])
    bdf_values = np.array([bdf["question_3_h"], bdf["question_4_h"]])
    delta_minutes = 60.0 * (be_values - bdf_values)
    bars = axes[0].barh(y, delta_minutes, color=BLUE_MID, height=0.48)
    axes[0].bar_label(bars, labels=[f"{value:.2f}" for value in delta_minutes], padding=3, fontsize=7)
    for yi, bdf_value, delta in zip(y, bdf_values, delta_minutes, strict=True):
        axes[0].text(
            max(0.10, delta * 0.04),
            yi,
            f"BDF {bdf_value:.3f} h",
            color="white",
            fontsize=6.4,
            ha="left",
            va="center",
        )
    axes[0].set_yticks(y, labels, fontproperties=FONT)
    axes[0].invert_yaxis()
    axes[0].set_xlim(0, max(delta_minutes) * 1.35)
    axes[0].set_xlabel(r"全隐式解相对BDF的差值/$\mathrm{min}$", fontproperties=FONT)
    axes[0].set_title("独立求解器差异", fontproperties=FONT_TITLE)
    add_panel_label(axes[0], "a")
    polish_axis(axes[0])

    extension = pd.DataFrame(audit["long_time_boundary_extension"]["cases"])
    extension = extension[extension["case"] != "air_extension_last"]
    extension["label"] = extension["case"].map(
        {
            "air_extension_tail_mean": "末段均值",
            "air_extension_smooth_tail_mean": "平滑渐近",
        }
    )
    xpos = np.arange(2)
    width = 0.30
    for question, offset, color, hatch in [(3, -width / 2, BLUE, None), (4, width / 2, ORANGE, "///")]:
        values = extension[extension["question"] == question]["change_percent"].to_numpy(float)
        axes[1].bar(
            xpos + offset,
            values,
            width,
            color=color,
            edgecolor=color,
            hatch=hatch,
            label=f"问题{question}",
        )
    axes[1].axhline(0, color="#333333", linewidth=0.8)
    axes[1].set_xticks(xpos, ["末段均值", "平滑渐近"], fontproperties=FONT_SMALL)
    axes[1].set_ylabel(r"相对末值保持的变化/$\%$", fontproperties=FONT)
    axes[1].set_title("长期炉况延拓", fontproperties=FONT_TITLE)
    axes[1].legend(prop=FONT_SMALL)
    add_panel_label(axes[1], "b")
    polish_axis(axes[1])

    sensitivity = pd.DataFrame(audit["diffusivity_sensitivity"])
    order = [
        "D_prefactor_minus20",
        "D_prefactor_plus20",
        "D_moisture_exponent_minus10",
        "D_moisture_exponent_plus10",
        "D_activation_exponent_minus5",
        "D_activation_exponent_plus5",
    ]
    tick_labels = [
        r"$D_0-20\%$",
        r"$D_0+20\%$",
        r"$a_C-10\%$",
        r"$a_C+10\%$",
        r"$a_T-5\%$",
        r"$a_T+5\%$",
    ]
    ypos = np.arange(len(order))
    for question, offset, color, marker in [(3, -0.10, BLUE, "o"), (4, 0.10, ORANGE, "s")]:
        values = (
            sensitivity[sensitivity["question"] == question]
            .set_index("case")
            .loc[order, "change_percent"]
            .to_numpy(float)
        )
        axes[2].scatter(values, ypos + offset, color=color, marker=marker, s=18, label=f"问题{question}")
    axes[2].axvline(0, color="#333333", linewidth=0.8)
    axes[2].set_yticks(ypos, tick_labels, fontproperties=FONT_SMALL)
    axes[2].invert_yaxis()
    axes[2].set_xlabel(r"烘干时长变化/$\%$", fontproperties=FONT)
    axes[2].set_title("扩散关系灵敏度", fontproperties=FONT_TITLE)
    axes[2].legend(prop=FONT_SMALL, loc="lower right")
    add_panel_label(axes[2], "c")
    polish_axis(axes[2])
    save_figure(fig, "problem_a_figure_11_reviewer_robustness_v01")


def main() -> None:
    setup_style()
    figure_inputs()
    plot_profile_pair(
        "problem_a_result_01_preheat_temperature_v01.csv",
        "problem_a_result_02_preheat_moisture_v01.csv",
        [0, 600, 1200, 1800],
        ["0 s", "600 s", "1200 s", "1800 s"],
        "problem_a_figure_05_preheat_profiles_cn_v03",
        "问题1：",
    )
    plot_profile_pair(
        "problem_a_result_05_q2_temperature_v01.csv",
        "problem_a_result_06_q2_moisture_v01.csv",
        [1800, 5400, 10800],
        ["0.5 h", "1.5 h", "3.0 h"],
        "problem_a_figure_06_q2_profiles_cn_v03",
        "问题2：",
    )
    figure_drying_endpoint()
    figure_counterfactual()
    figure_sensitivity()
    figure_latent_heat_audit()
    figure_reviewer_robustness()


if __name__ == "__main__":
    main()
