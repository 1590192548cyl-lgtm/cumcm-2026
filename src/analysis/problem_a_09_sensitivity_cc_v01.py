"""Evaluate one-at-a-time sensitivity of Problem A drying times."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import src.models.problem_a_03_full_drying_pde_cc_v01 as drying


MAX_TIME_S = 180 * 3600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--air-input",
        type=Path,
        default=Path("data/raw/problem_a_raw_attachment_1_v01.xlsx"),
    )
    parser.add_argument(
        "--radius-input",
        type=Path,
        default=Path("data/raw/problem_a_raw_attachment_2_v01.xlsx"),
    )
    parser.add_argument("--intervals", type=int, default=320)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/results/problem_a_result_12_sensitivity_v01.json"),
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=Path("outputs/tables/problem_a_table_06_sensitivity_v01.csv"),
    )
    return parser.parse_args()


def solve_pair(
    *,
    name: str,
    air_data: np.ndarray,
    radius_time_s: np.ndarray,
    radius_m: np.ndarray,
    intervals: int,
    h_factor: float = 1.0,
    hm_factor: float = 1.0,
) -> dict[str, float | str]:
    original_h, original_hm = drying.H, drying.HM
    drying.H = original_h * h_factor
    drying.HM = original_hm * hm_factor
    try:
        q3_solver = drying.RadialDryingSolver(
            intervals, drying.appendix3_model(), air_data
        )
        q3 = q3_solver.solve_sampled(
            MAX_TIME_S,
            60,
            np.array([0.0]),
            stop_at_dry=True,
            chunk_s=3600,
        )
        q4_solver = drying.RadialDryingSolver(
            intervals,
            drying.appendix4_model(),
            air_data,
            radius_time_s=radius_time_s,
            radius_m=radius_m,
        )
        q4 = q4_solver.solve_sampled(
            MAX_TIME_S,
            60,
            np.array([0.0]),
            include_surface=True,
            stop_at_dry=True,
            chunk_s=3600,
        )
    finally:
        drying.H, drying.HM = original_h, original_hm

    q3_time_h = float(q3["drying_time_s"]) / 3600.0
    q4_time_h = float(q4["drying_time_s"]) / 3600.0
    if not np.isfinite(q3_time_h) or not np.isfinite(q4_time_h):
        raise RuntimeError(
            f"Sensitivity case {name} did not reach the threshold: "
            f"q3={q3_time_h}, q4={q4_time_h}"
        )
    return {
        "case": name,
        "h_factor": h_factor,
        "hm_factor": hm_factor,
        "terminal_air_temperature_c": float(air_data[-1, 1]),
        "terminal_air_moisture_kg_per_kg": float(air_data[-1, 2]),
        "q3_drying_time_h": q3_time_h,
        "q4_drying_time_h": q4_time_h,
    }


def main() -> None:
    args = parse_args()
    if args.intervals < 160 or args.intervals % 20 != 0:
        raise ValueError("--intervals must be a multiple of 20 and at least 160")

    base_air = drying.read_numeric_excel(args.air_input, 3)
    radius_data_cm = drying.read_numeric_excel(args.radius_input, 2)
    radius_time_s = radius_data_cm[:, 0]
    radius_m = radius_data_cm[:, 1] / 100.0

    specifications = [
        ("baseline", 1.0, 1.0, 0.0, 1.0),
        ("h_minus_20pct", 0.8, 1.0, 0.0, 1.0),
        ("h_plus_20pct", 1.2, 1.0, 0.0, 1.0),
        ("hm_minus_20pct", 1.0, 0.8, 0.0, 1.0),
        ("hm_plus_20pct", 1.0, 1.2, 0.0, 1.0),
        ("terminal_temperature_minus_2c", 1.0, 1.0, -2.0, 1.0),
        ("terminal_temperature_plus_2c", 1.0, 1.0, 2.0, 1.0),
        ("terminal_moisture_minus_20pct", 1.0, 1.0, 0.0, 0.8),
        ("terminal_moisture_plus_20pct", 1.0, 1.0, 0.0, 1.2),
    ]
    rows: list[dict[str, float | str]] = []
    for name, h_factor, hm_factor, temperature_offset, moisture_factor in specifications:
        air_data = base_air.copy()
        air_data[-1, 1] += temperature_offset
        air_data[-1, 2] *= moisture_factor
        rows.append(
            solve_pair(
                name=name,
                air_data=air_data,
                radius_time_s=radius_time_s,
                radius_m=radius_m,
                intervals=args.intervals,
                h_factor=h_factor,
                hm_factor=hm_factor,
            )
        )

    baseline = rows[0]
    for row in rows:
        for question in ("q3", "q4"):
            value_key = f"{question}_drying_time_h"
            row[f"{question}_change_percent"] = 100.0 * (
                float(row[value_key]) - float(baseline[value_key])
            ) / float(baseline[value_key])

    report = {
        "purpose": (
            "One-at-a-time robustness analysis on a 320-interval grid. "
            "Percent changes are normalized to the same-grid baseline and are not official outputs."
        ),
        "grid_intervals": args.intervals,
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(args.table_output, index=False, float_format="%.8f")
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    print(args.output)
    print(args.table_output)


if __name__ == "__main__":
    main()
