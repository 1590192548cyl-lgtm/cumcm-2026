"""Run a 2x2 material-correlation and radius-path counterfactual for Problem A."""

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

from src.models.problem_a_03_full_drying_pde_cc_v01 import (
    DRYING_THRESHOLD,
    RadialDryingSolver,
    appendix3_model,
    appendix4_model,
    read_numeric_excel,
)


MAX_COUNTERFACTUAL_TIME_S = 180 * 3600


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
    parser.add_argument("--intervals", type=int, default=640)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "outputs/results/problem_a_result_11_counterfactual_comparison_v01.json"
        ),
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=Path(
            "outputs/tables/problem_a_table_05_counterfactual_comparison_v01.csv"
        ),
    )
    return parser.parse_args()


def solve_case(
    *,
    name: str,
    material,
    air_data: np.ndarray,
    intervals: int,
    radius_time_s: np.ndarray | None = None,
    radius_m: np.ndarray | None = None,
) -> dict[str, float | str]:
    solver = RadialDryingSolver(
        intervals,
        material,
        air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
    )
    result = solver.solve_sampled(
        MAX_COUNTERFACTUAL_TIME_S,
        60,
        np.array([0.0]),
        include_surface=True,
        stop_at_dry=True,
        chunk_s=3600,
    )
    drying_time_s = float(result["drying_time_s"])
    if not np.isfinite(drying_time_s):
        raise RuntimeError(f"{name} did not reach {DRYING_THRESHOLD} within 180 h")
    return {
        "case": name,
        "material": material.name,
        "radius_path": "measured shrinkage" if radius_time_s is not None else "fixed 2 cm",
        "drying_time_s": drying_time_s,
        "drying_time_h": drying_time_s / 3600.0,
    }


def main() -> None:
    args = parse_args()
    if args.intervals < 160 or args.intervals % 20 != 0:
        raise ValueError("--intervals must be a multiple of 20 and at least 160")

    air_data = read_numeric_excel(args.air_input, 3)
    radius_data_cm = read_numeric_excel(args.radius_input, 2)
    radius_time_s = radius_data_cm[:, 0]
    radius_m = radius_data_cm[:, 1] / 100.0

    appendix3 = appendix3_model()
    appendix4 = appendix4_model()
    cases = [
        solve_case(
            name="appendix3_fixed",
            material=appendix3,
            air_data=air_data,
            intervals=args.intervals,
        ),
        solve_case(
            name="appendix3_shrinking",
            material=appendix3,
            air_data=air_data,
            intervals=args.intervals,
            radius_time_s=radius_time_s,
            radius_m=radius_m,
        ),
        solve_case(
            name="appendix4_fixed",
            material=appendix4,
            air_data=air_data,
            intervals=args.intervals,
        ),
        solve_case(
            name="appendix4_shrinking",
            material=appendix4,
            air_data=air_data,
            intervals=args.intervals,
            radius_time_s=radius_time_s,
            radius_m=radius_m,
        ),
    ]
    by_name = {str(case["case"]): case for case in cases}

    def reduction(fixed_name: str, shrinking_name: str) -> float:
        fixed = float(by_name[fixed_name]["drying_time_h"])
        shrinking = float(by_name[shrinking_name]["drying_time_h"])
        return 100.0 * (fixed - shrinking) / fixed

    comparison = {
        "purpose": (
            "Separate the radius-path effect from the material-correlation effect; "
            "these 640-interval cases are robustness evidence rather than official outputs."
        ),
        "grid_intervals": args.intervals,
        "threshold_kg_per_kg": DRYING_THRESHOLD,
        "cases": cases,
        "within_material_shrinkage_reduction_percent": {
            "appendix3": reduction("appendix3_fixed", "appendix3_shrinking"),
            "appendix4": reduction("appendix4_fixed", "appendix4_shrinking"),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(cases).to_csv(args.table_output, index=False, float_format="%.8f")
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    print(args.output)
    print(args.table_output)


if __name__ == "__main__":
    main()
