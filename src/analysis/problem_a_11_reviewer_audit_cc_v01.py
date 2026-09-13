"""Close the numerical and modelling issues raised in the second paper review.

The script keeps the official attachment data unchanged and audits six items:
event-root accuracy, display-safe termination, long-time boundary extension,
diffusivity sensitivity, shrinkage interpolation/degeneration, and the integral
balance of the selected material-coordinate PDE.  Results are evidence files;
they do not silently replace the four required workbooks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import src.models.problem_a_03_full_drying_pde_cc_v01 as drying


MAX_TIME_S = 180 * 3600
TEAMMATE_BE_BASELINE = {
    "question_3_h": 57.2107679919847,
    "question_4_h": 50.863359389520554,
    "grid_intervals": 640,
    "method": "backward Euler finite volume, arithmetic face average",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intervals", type=int, default=640)
    parser.add_argument("--fine-intervals", type=int, default=1280)
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
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/results/problem_a_result_17_reviewer_audit_v01.json"),
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=Path("outputs/tables/problem_a_table_08_reviewer_audit_v01.csv"),
    )
    return parser.parse_args()


def perturbed_material(
    question: int,
    *,
    prefactor_scale: float = 1.0,
    moisture_exponent_scale: float = 1.0,
    activation_exponent_scale: float = 1.0,
) -> drying.MaterialModel:
    if question == 3:
        base = drying.appendix3_model()
        prefactor, moisture_exponent = 2.4e-3, 0.45
    elif question == 4:
        base = drying.appendix4_model()
        prefactor, moisture_exponent = 4.2e-4, 0.30
    else:
        raise ValueError("question must be 3 or 4")

    def diffusivity(c: np.ndarray, t_k: np.ndarray) -> np.ndarray:
        c_safe = np.maximum(c, 1.0e-9)
        return (
            prefactor
            * prefactor_scale
            * np.exp(-moisture_exponent * moisture_exponent_scale / c_safe)
            * np.exp(-3850.0 * activation_exponent_scale / t_k)
        )

    return replace(base, diffusivity=diffusivity)


def solve_case(
    *,
    question: int,
    material: drying.MaterialModel,
    air_data: np.ndarray,
    radius_time_s: np.ndarray,
    radius_m: np.ndarray,
    intervals: int,
    face_average: str = "arithmetic",
    radius_interpolation: str = "linear",
    air_extension_mode: str = "last",
    rtol: float = 2.0e-7,
    max_step_s: float = 60.0,
    record_dt_s: int = 60,
    constant_radius_path: bool = False,
) -> tuple[dict, drying.RadialDryingSolver]:
    use_radius_time = None
    use_radius = None
    if question == 4:
        use_radius_time = radius_time_s
        use_radius = radius_m
        if constant_radius_path:
            use_radius = np.full_like(radius_m, drying.INITIAL_RADIUS_M)
    solver = drying.RadialDryingSolver(
        intervals,
        material,
        air_data,
        radius_time_s=use_radius_time,
        radius_m=use_radius,
        face_average=face_average,
        radius_interpolation=radius_interpolation,
        air_extension_mode=air_extension_mode,
        rtol=rtol,
        max_step_s=max_step_s,
    )
    result = solver.solve_sampled(
        MAX_TIME_S,
        record_dt_s,
        np.array([0.0]),
        include_surface=True,
        stop_at_dry=True,
        stop_threshold=drying.DISPLAY_SAFE_THRESHOLD,
        chunk_s=1800,
    )
    if not np.isfinite(result["threshold_time_s"]):
        raise RuntimeError(f"Question {question} did not reach the threshold.")
    return result, solver


def result_row(case: str, question: int, result: dict, baseline_h: float) -> dict:
    time_h = float(result["threshold_time_s"]) / 3600.0
    return {
        "case": case,
        "question": question,
        "drying_time_h": time_h,
        "change_percent": 100.0 * (time_h - baseline_h) / baseline_h,
    }


def material_coordinate_balance(result: dict, solver: drying.RadialDryingSolver) -> dict:
    n = solver.n_nodes
    xi = solver.xi
    faces = np.empty(n + 1)
    faces[0], faces[-1] = 0.0, 1.0
    faces[1:-1] = 0.5 * (xi[:-1] + xi[1:])
    weights = 0.5 * (faces[1:] ** 2 - faces[:-1] ** 2)
    final_c = np.asarray(result["final_state"])[n:]
    initial_integral = float(np.sum(weights * drying.INITIAL_C))
    final_integral = float(np.sum(weights * final_c))

    times = np.asarray(result["time_s"], dtype=float)
    sampled_c = np.asarray(result["moisture"], dtype=float)
    surface_c = sampled_c[:, -1]
    air_c = np.asarray([solver.air_at(t)[1] for t in times])
    radii = np.asarray([solver.radius_at(t) for t in times])
    boundary_rate = drying.HM * (air_c - surface_c) / radii
    boundary_integral = float(np.trapezoid(boundary_rate, times))
    state_change = final_integral - initial_integral
    residual = state_change - boundary_integral
    return {
        "meaning": (
            "Integral balance of the selected effective material-coordinate PDE; "
            "not a full deforming porous-medium mass balance."
        ),
        "state_change": state_change,
        "integrated_boundary_rate": boundary_integral,
        "absolute_residual": residual,
        "relative_residual": residual / max(abs(state_change), 1.0e-30),
        "quadrature_interval_s": float(np.max(np.diff(times))),
    }


def main() -> None:
    args = parse_args()
    air_data = drying.read_numeric_excel(args.air_input, 3)
    radius_data_cm = drying.read_numeric_excel(args.radius_input, 2)
    radius_time_s = radius_data_cm[:, 0]
    radius_m = radius_data_cm[:, 1] / 100.0

    q3_base, q3_solver = solve_case(
        question=3,
        material=drying.appendix3_model(),
        air_data=air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
        intervals=args.intervals,
    )
    q4_base, q4_solver = solve_case(
        question=4,
        material=drying.appendix4_model(),
        air_data=air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
        intervals=args.intervals,
    )
    q3_base_h = float(q3_base["threshold_time_s"]) / 3600.0
    q4_base_h = float(q4_base["threshold_time_s"]) / 3600.0
    rows = [
        result_row("baseline", 3, q3_base, q3_base_h),
        result_row("baseline", 4, q4_base, q4_base_h),
    ]

    tolerance_rows = []
    for rtol, max_step in [(2.0e-6, 60.0), (2.0e-7, 60.0), (2.0e-8, 30.0)]:
        for question, material, baseline_h in [
            (3, drying.appendix3_model(), q3_base_h),
            (4, drying.appendix4_model(), q4_base_h),
        ]:
            result, _ = solve_case(
                question=question,
                material=material,
                air_data=air_data,
                radius_time_s=radius_time_s,
                radius_m=radius_m,
                intervals=args.intervals,
                rtol=rtol,
                max_step_s=max_step,
            )
            row = result_row(f"rtol={rtol:g},max_step={max_step:g}", question, result, baseline_h)
            tolerance_rows.append(row)
            rows.append(row)

    extension_rows = []
    for mode in ["last", "tail_mean", "smooth_tail_mean"]:
        for question, material, baseline_h in [
            (3, drying.appendix3_model(), q3_base_h),
            (4, drying.appendix4_model(), q4_base_h),
        ]:
            result, _ = solve_case(
                question=question,
                material=material,
                air_data=air_data,
                radius_time_s=radius_time_s,
                radius_m=radius_m,
                intervals=args.intervals,
                air_extension_mode=mode,
            )
            row = result_row(f"air_extension_{mode}", question, result, baseline_h)
            extension_rows.append(row)
            rows.append(row)

    diffusivity_rows = []
    perturbations = [
        ("D_prefactor_minus20", {"prefactor_scale": 0.8}),
        ("D_prefactor_plus20", {"prefactor_scale": 1.2}),
        ("D_moisture_exponent_minus10", {"moisture_exponent_scale": 0.9}),
        ("D_moisture_exponent_plus10", {"moisture_exponent_scale": 1.1}),
        ("D_activation_exponent_minus5", {"activation_exponent_scale": 0.95}),
        ("D_activation_exponent_plus5", {"activation_exponent_scale": 1.05}),
    ]
    for name, kwargs in perturbations:
        for question, baseline_h in [(3, q3_base_h), (4, q4_base_h)]:
            result, _ = solve_case(
                question=question,
                material=perturbed_material(question, **kwargs),
                air_data=air_data,
                radius_time_s=radius_time_s,
                radius_m=radius_m,
                intervals=args.intervals,
            )
            row = result_row(name, question, result, baseline_h)
            diffusivity_rows.append(row)
            rows.append(row)

    q4_pchip, _ = solve_case(
        question=4,
        material=drying.appendix4_model(),
        air_data=air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
        intervals=args.intervals,
        radius_interpolation="pchip",
    )
    pchip_row = result_row("radius_pchip", 4, q4_pchip, q4_base_h)
    rows.append(pchip_row)

    q4_fixed_direct, _ = solve_case(
        question=3,
        material=drying.appendix4_model(),
        air_data=air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
        intervals=args.intervals,
    )
    q4_fixed_path, _ = solve_case(
        question=4,
        material=drying.appendix4_model(),
        air_data=air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
        intervals=args.intervals,
        constant_radius_path=True,
    )
    degeneration_difference_s = abs(
        float(q4_fixed_direct["threshold_time_s"])
        - float(q4_fixed_path["threshold_time_s"])
    )

    legacy_extreme_rows = []
    extreme_air = air_data.copy()
    extreme_air[-1, 2] *= 0.8
    for intervals in sorted({320, args.fine_intervals}):
        result, _ = solve_case(
            question=3,
            material=drying.appendix3_model(),
            air_data=extreme_air,
            radius_time_s=radius_time_s,
            radius_m=radius_m,
            intervals=intervals,
            face_average="harmonic",
        )
        legacy_extreme_rows.append(
            {
                "intervals": intervals,
                "drying_time_h": float(result["threshold_time_s"]) / 3600.0,
                "note": "legacy perturbation changes the final observed point itself",
            }
        )

    safety = {}
    for question, result in [(3, q3_base), (4, q4_base)]:
        final_max = float(np.nanmax(np.asarray(result["moisture"])[-1]))
        safety[f"question_{question}"] = {
            "operational_end_s": int(result["operational_end_s"]),
            "computed_final_max": final_max,
            "error_margin": drying.DISCRETIZATION_MARGIN,
            "upper_bound": final_max + drying.DISCRETIZATION_MARGIN,
            "display_threshold": drying.DISPLAY_ROUNDING_THRESHOLD,
            "verified": bool(
                final_max + drying.DISCRETIZATION_MARGIN
                < drying.DISPLAY_ROUNDING_THRESHOLD
            ),
        }

    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    report = {
        "data_contract": {
            "raw_attachments_unchanged": True,
            "air_attachment_sha256": sha256(args.air_input),
            "radius_attachment_sha256": sha256(args.radius_input),
            "teammate_update_interpretation": (
                "The teammate branch changes discretization and reporting; the two raw "
                "attachment hashes are identical to the current workspace inputs."
            ),
        },
        "teammate_backward_euler_baseline": TEAMMATE_BE_BASELINE,
        "bdf_event_baseline": {
            "grid_intervals": args.intervals,
            "face_average": "arithmetic",
            "rtol": 2.0e-7,
            "max_step_s": 60.0,
            "question_3_h": q3_base_h,
            "question_4_h": q4_base_h,
        },
        "event_tolerance_and_step_audit": tolerance_rows,
        "display_safety": safety,
        "long_time_boundary_extension": {
            "tail_window_s": [9000, 14400],
            "tail_temperature_mean_c": q3_solver.air_tail_temperature_c,
            "tail_moisture_mean_kg_per_kg": q3_solver.air_tail_moisture,
            "cases": extension_rows,
        },
        "diffusivity_sensitivity": diffusivity_rows,
        "radius_interpolation": pchip_row,
        "constant_radius_degeneration": {
            "direct_fixed_domain_h": float(q4_fixed_direct["threshold_time_s"]) / 3600.0,
            "moving_domain_with_R_equal_R0_h": float(q4_fixed_path["threshold_time_s"]) / 3600.0,
            "absolute_difference_s": degeneration_difference_s,
            "passed": bool(degeneration_difference_s < 1.0e-4),
        },
        "question_4_effective_pde_integral_balance": material_coordinate_balance(
            q4_base, q4_solver
        ),
        "legacy_167h_branch_recheck": legacy_extreme_rows,
        "wording_contract": {
            "allowed": (
                "The finite-volume scheme satisfies the integral balance of the selected "
                "effective PDE; this does not establish a full deforming porous-medium "
                "mass balance."
            ),
            "latent_heat": (
                "The latent-heat calculation is an identifiability and scale audit, not "
                "a validated latent-heat-enhanced prediction."
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.table_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pd.DataFrame(rows).to_csv(args.table_output, index=False, float_format="%.8f")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
