# -*- coding: utf-8 -*-
"""数据预处理：读取附件 1（烘房温度、水分浓度）与附件 2（药材半径），
做质量检查，落盘为干净的 CSV，并生成预处理报告。

设计要点
--------
1. 附件 1 的采样间隔 60 s，而结果要求每 1 s 一个值，因此必须插值。
   这里采用分段线性插值：不引入额外光滑假设，也不会像三次样条那样
   在平台段产生过冲（虚构的峰值/谷值）。超过数据范围时按端点值常数外延，
   便于问题 3、4 把边界条件推广到 2~3 天。
2. 附件 2 的半径数据时间跨度 0~259200 s（3 天），间隔 1800 s，
   问题 4 的收缩模型需要用到，这里一并清洗并检查单调性。
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent.parent
ATTACH_DIR = ROOT / "data" / "raw"
DATA_DIR = ROOT / "data" / "processed"


def _read_attachment(path):
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


class AmbientAir:
    """烘房（环境）温度与水分浓度随时间的插值对象。"""

    def __init__(self, t, T, C):
        self.t = np.asarray(t, dtype=float)
        self.T = np.asarray(T, dtype=float)
        self.C = np.asarray(C, dtype=float)

    def T_air(self, t):
        # np.interp 在区间外自动取端点值（常数外延）
        return float(np.interp(t, self.t, self.T))

    def C_air(self, t):
        return float(np.interp(t, self.t, self.C))


def load_ambient():
    """读取清洗后的附件 1 数据（若未预处理则自动先跑一遍）。"""
    csv = DATA_DIR / "problem_a_processed_ambient_air_v01.csv"
    if not csv.exists():
        run_preprocess(verbose=False)
    df = pd.read_csv(csv)
    return AmbientAir(df["时间_s"].to_numpy(), df["温度_C"].to_numpy(),
                      df["水分浓度_kgkg"].to_numpy())


def load_radius():
    """读取清洗后的附件 2 半径数据。"""
    csv = DATA_DIR / "problem_a_processed_radius_v01.csv"
    if not csv.exists():
        run_preprocess(verbose=False)
    return pd.read_csv(csv)


def run_preprocess(verbose=True):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {"notes": [], "checks": [], "files": []}

    # ---------------- 附件 1 ----------------
    f1 = ATTACH_DIR / "problem_a_raw_attachment_1_v01.xlsx"
    raw = _read_attachment(f1)
    report["附件1_原始列名"] = list(raw.columns)
    report["附件1_原始行数"] = int(len(raw))

    df = raw.rename(columns={"时间": "时间_s", "温度": "温度_C", "水分浓度": "水分浓度_kgkg"})
    df = df[["时间_s", "温度_C", "水分浓度_kgkg"]].apply(pd.to_numeric, errors="coerce")

    n_nan = int(df.isna().sum().sum())
    dup = int(df["时间_s"].duplicated().sum())
    dt = np.diff(df["时间_s"].to_numpy())
    dt_uniq = np.unique(dt)
    mono = bool(np.all(dt > 0))

    report["checks"].append(f"附件1：缺失值 {n_nan} 个；重复时间 {dup} 个；"
                            f"时间严格递增={mono}；采样间隔={dt_uniq.tolist()} s")
    assert n_nan == 0, "附件1 存在缺失值"
    assert dup == 0, "附件1 存在重复时间"
    assert mono, "附件1 时间列非严格递增"
    assert dt_uniq.size == 1, "附件1 采样间隔不均匀"

    t = df["时间_s"].to_numpy(float)
    T = df["温度_C"].to_numpy(float)
    C = df["水分浓度_kgkg"].to_numpy(float)
    report["附件1_时间范围_s"] = [float(t[0]), float(t[-1])]
    report["附件1_温度范围_C"] = [float(T.min()), float(T.max())]
    report["附件1_水分浓度范围"] = [float(C.min()), float(C.max())]

    # 平台段抖动（用后 1/4 数据估计），判断是否需要平滑
    tail = slice(max(1, len(t) - len(t) // 4), len(t))
    report["附件1_平台段温度标准差_C"] = round(float(np.std(T[tail], ddof=1)), 4)
    report["附件1_平台段温度峰峰值_C"] = round(float(np.ptp(T[tail])), 4)
    report["附件1_水分浓度是否单调"] = bool(np.all(np.diff(C) >= 0))
    report["notes"].append(
        "附件1 平台段温度存在 ±0.1 摄氏度量级的测量抖动，属正常数据噪声；"
        "采用线性插值，不做人为平滑，避免影响表 1 的四位小数结果。")

    # 平台值（用于问题 2~4 的恒温干燥阶段边界条件）
    plateau_T = float(np.mean(T[t >= 7200]))
    plateau_C = float(np.mean(C[t >= 7200]))
    report["恒温阶段平台值"] = {"温度_C": round(plateau_T, 4),
                                "水分浓度_kgkg": round(plateau_C, 4)}
    report["notes"].append(
        f"附件1 仅覆盖 0~{int(t[-1])} s（4 h）。数据在 7200 s 后进入平台，"
        f"温度约 {plateau_T:.2f} 摄氏度、水分浓度约 {plateau_C:.4f} kg/kg，"
        "问题 3、4 需要把边界条件按该平台值常数外延到 2~3 天。")

    # 线性插值重采样到 1 s（问题 1、2 需要）
    t_fine = np.arange(t[0], t[-1] + 1e-9, 1.0)
    fine = pd.DataFrame({
        "时间_s": t_fine,
        "温度_C": np.interp(t_fine, t, T),
        "水分浓度_kgkg": np.interp(t_fine, t, C),
    })
    clean = df.copy()
    out1 = DATA_DIR / "problem_a_processed_ambient_air_v01.csv"
    clean.to_csv(out1, index=False, encoding="utf-8-sig")
    out1b = DATA_DIR / "problem_a_processed_ambient_air_1s_v01.csv"
    fine.to_csv(out1b, index=False, encoding="utf-8-sig")
    report["files"] += [str(out1), str(out1b)]

    # 初始条件一致性检查
    report["checks"].append(
        f"附件1 初始烘房温度 = {T[0]:.3f} 摄氏度，与药材初温 28 摄氏度一致："
        f"{'是' if abs(T[0] - 28.0) < 1e-9 else '否'}")
    report["checks"].append(
        f"t=1800 s 时烘房温度 = {np.interp(1800.0, t, T):.4f} 摄氏度，"
        f"水分浓度 = {np.interp(1800.0, t, C):.4f} kg/kg（问题 1 的边界终值）")

    # ---------------- 附件 2 ----------------
    f2 = ATTACH_DIR / "problem_a_raw_attachment_2_v01.xlsx"
    raw2 = _read_attachment(f2)
    report["附件2_原始列名"] = list(raw2.columns)
    report["附件2_原始行数"] = int(len(raw2))

    df2 = raw2.rename(columns={"时间": "时间_s", "半径": "半径_cm"})
    df2 = df2[["时间_s", "半径_cm"]].apply(pd.to_numeric, errors="coerce")
    n_nan2 = int(df2.isna().sum().sum())
    dup2 = int(df2["时间_s"].duplicated().sum())
    dt2 = np.diff(df2["时间_s"].to_numpy())
    mono2 = bool(np.all(dt2 > 0))
    r2 = df2["半径_cm"].to_numpy(float)
    n_up = int(np.sum(np.diff(r2) > 1e-9))
    report["checks"].append(
        f"附件2：缺失值 {n_nan2} 个；重复时间 {dup2} 个；时间严格递增={mono2}；"
        f"采样间隔={np.unique(dt2).tolist()} s；半径非单调上升的点 {n_up} 个；"
        f"是否恒为正={bool(np.all(r2 > 0))}")
    assert n_nan2 == 0 and dup2 == 0 and mono2, "附件2 数据质量检查未通过"
    assert np.all(r2 > 0), "附件2 出现非正半径"
    report["附件2_半径范围_cm"] = [float(r2.min()), float(r2.max())]
    report["附件2_时间范围_s"] = [float(df2["时间_s"].iloc[0]), float(df2["时间_s"].iloc[-1])]
    report["附件2_总收缩率"] = round(float(1.0 - r2.min() / r2.max()), 4)
    report["notes"].append(
        f"附件2 显示药材半径由 2.0 cm 收缩到 {r2.min():.3f} cm"
        f"（收缩 {(1 - r2.min() / r2.max()) * 100:.1f}%），且 20 h 后基本稳定；"
        "问题 4 必须按动边界（坐标变换）处理，不能直接用固定半径网格。")

    out2 = DATA_DIR / "problem_a_processed_radius_v01.csv"
    df2.to_csv(out2, index=False, encoding="utf-8-sig")
    report["files"].append(str(out2))

    (DATA_DIR / "problem_a_processed_data_quality_report_v01.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 数据预处理报告", ""]
    lines.append("## 检查结果")
    lines += [f"- {c}" for c in report["checks"]]
    lines.append("")
    lines.append("## 处理说明")
    lines += [f"- {c}" for c in report["notes"]]
    lines.append("")
    lines.append("## 生成文件")
    lines += [f"- `{c}`" for c in report["files"]]
    (DATA_DIR / "problem_a_processed_data_quality_report_v01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if verbose:
        for c in report["checks"]:
            print("  [检查]", c)
        for c in report["notes"]:
            print("  [说明]", c)
    return report


if __name__ == "__main__":
    run_preprocess()
