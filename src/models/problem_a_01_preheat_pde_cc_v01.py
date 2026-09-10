"""Problem A, question 1: radial heat and moisture transfer during preheating.

The medicinal material is approximated as a long cylinder. Axial gradients are
neglected and the coupled fields are solved on the radius with a conservative
node-centred finite-volume method. The air conditions are linearly interpolated
from attachment 1. This script writes machine-readable results, a profile figure,
and numerical validation diagnostics; it never modifies the raw workbook.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix


RADIUS_M = 0.02
INITIAL_T_C = 28.0
INITIAL_C = 2.55
RHO = 820.0
CP = 2600.0
K = 0.36
H = 25.0
HM = 8.0e-7
END_TIME_S = 1800
TARGET_TIMES_S = np.array([100, 300, 600, 900, 1200, 1500, 1800])
TARGET_RADII_CM = np.arange(0.0, 2.0 + 1.0e-12, 0.1)
KEY_RADII_CM = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
PROFILE_TIMES_S = np.array([0, 100, 300, 600, 900, 1200, 1500, 1800])


def moisture_diffusivity(c: np.ndarray) -> np.ndarray:
    """Moisture-dependent diffusivity in square metres per second."""

    c_safe = np.maximum(c, 1.0e-9)
    return 7.0e-9 * np.exp(-0.89 / c_safe)


def load_air_conditions(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    frame = pd.read_excel(path, sheet_name=0)
    if frame.shape[1] < 3:
        raise ValueError("Attachment 1 must contain time, temperature and moisture columns.")
    values = frame.iloc[:, :3].apply(pd.to_numeric, errors="raise").to_numpy(float)
    time_s, temperature_c, moisture = values.T
    if np.any(np.diff(time_s) <= 0):
        raise ValueError("Air-condition time values must be strictly increasing.")
    if time_s[0] > 0 or time_s[-1] < END_TIME_S:
        raise ValueError("Air-condition data do not cover the 0--1800 s interval.")
    return time_s, temperature_c, moisture


def jacobian_sparsity(n_nodes: int):
    size = 2 * n_nodes
    pattern = lil_matrix((size, size), dtype=int)
    for offset in (0, n_nodes):
        for i in range(n_nodes):
            pattern[offset + i, offset + i] = 1
            if i > 0:
                pattern[offset + i, offset + i - 1] = 1
            if i + 1 < n_nodes:
                pattern[offset + i, offset + i + 1] = 1
    return pattern.tocsr()


def solve_grid(
    intervals: int,
    air_time_s: np.ndarray,
    air_temperature_c: np.ndarray,
    air_moisture: np.ndarray,
    output_time_s: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Solve on a grid with ``intervals`` radial intervals."""

    radius = np.linspace(0.0, RADIUS_M, intervals + 1)
    dr = radius[1] - radius[0]
    face_radius = np.empty(intervals + 2)
    face_radius[0] = 0.0
    face_radius[-1] = RADIUS_M
    face_radius[1:-1] = 0.5 * (radius[:-1] + radius[1:])
    control_volume = 0.5 * (face_radius[1:] ** 2 - face_radius[:-1] ** 2)

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        temperature = y[: intervals + 1]
        moisture = y[intervals + 1 :]
        t_air = np.interp(t, air_time_s, air_temperature_c)
        c_air = np.interp(t, air_time_s, air_moisture)

        heat_flux_like = np.empty(intervals + 2)
        heat_flux_like[0] = 0.0
        heat_flux_like[1:-1] = K * np.diff(temperature) / dr
        heat_flux_like[-1] = H * (t_air - temperature[-1])
        dtemperature_dt = (
            face_radius[1:] * heat_flux_like[1:]
            - face_radius[:-1] * heat_flux_like[:-1]
        ) / (RHO * CP * control_volume)

        diffusivity = moisture_diffusivity(moisture)
        face_diffusivity = (
            2.0
            * diffusivity[:-1]
            * diffusivity[1:]
            / np.maximum(diffusivity[:-1] + diffusivity[1:], 1.0e-30)
        )
        moisture_flux_like = np.empty(intervals + 2)
        moisture_flux_like[0] = 0.0
        moisture_flux_like[1:-1] = face_diffusivity * np.diff(moisture) / dr
        moisture_flux_like[-1] = HM * (c_air - moisture[-1])
        dmoisture_dt = (
            face_radius[1:] * moisture_flux_like[1:]
            - face_radius[:-1] * moisture_flux_like[:-1]
        ) / control_volume
        return np.concatenate([dtemperature_dt, dmoisture_dt])

    y0 = np.concatenate(
        [
            np.full(intervals + 1, INITIAL_T_C),
            np.full(intervals + 1, INITIAL_C),
        ]
    )
    atol = np.concatenate(
        [np.full(intervals + 1, 1.0e-9), np.full(intervals + 1, 1.0e-10)]
    )
    solution = solve_ivp(
        rhs,
        (0.0, float(END_TIME_S)),
        y0,
        method="BDF",
        t_eval=output_time_s,
        rtol=1.0e-8,
        atol=atol,
        jac_sparsity=jacobian_sparsity(intervals + 1),
    )
    if not solution.success:
        raise RuntimeError(f"PDE solver failed: {solution.message}")
    temperature = solution.y[: intervals + 1].T
    moisture = solution.y[intervals + 1 :].T
    return radius, temperature, moisture


def sample_radius(
    radius_m: np.ndarray, values: np.ndarray, target_radius_cm: np.ndarray
) -> np.ndarray:
    target_radius_m = target_radius_cm / 100.0
    return np.vstack(
        [np.interp(target_radius_m, radius_m, row) for row in values]
    )


def radial_average(radius_m: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Area-weighted cylindrical cross-section average."""

    dr = radius_m[1] - radius_m[0]
    face_radius = np.empty(radius_m.size + 1)
    face_radius[0] = 0.0
    face_radius[-1] = RADIUS_M
    face_radius[1:-1] = 0.5 * (radius_m[:-1] + radius_m[1:])
    volume = 0.5 * (face_radius[1:] ** 2 - face_radius[:-1] ** 2)
    return values @ volume / (0.5 * RADIUS_M**2)


def write_wide_csv(
    path: Path, time_s: np.ndarray, values: np.ndarray, radii_cm: np.ndarray
) -> None:
    columns = ["time_s"] + [f"r_{radius:.1f}_cm" for radius in radii_cm]
    frame = pd.DataFrame(np.column_stack([time_s, values]), columns=columns)
    frame["time_s"] = frame["time_s"].astype(int)
    frame.to_csv(path, index=False, float_format="%.8f")


def make_key_table(
    output_dir: Path,
    time_s: np.ndarray,
    temperature: np.ndarray,
    moisture: np.ndarray,
) -> pd.DataFrame:
    time_index = np.searchsorted(time_s, TARGET_TIMES_S)
    radius_index = np.searchsorted(TARGET_RADII_CM, KEY_RADII_CM)
    rows: list[dict[str, float | int]] = []
    for ti, t in zip(time_index, TARGET_TIMES_S, strict=True):
        for ri, r in zip(radius_index, KEY_RADII_CM, strict=True):
            rows.append(
                {
                    "time_s": int(t),
                    "radius_cm": float(r),
                    "temperature_c": float(temperature[ti, ri]),
                    "moisture_kg_per_kg": float(moisture[ti, ri]),
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(
        output_dir / "problem_a_table_01_preheat_key_values_v01.csv",
        index=False,
        float_format="%.8f",
    )
    return frame


def plot_profiles(
    path: Path,
    time_s: np.ndarray,
    radii_cm: np.ndarray,
    temperature: np.ndarray,
    moisture: np.ndarray,
) -> None:
    indices = np.searchsorted(time_s, PROFILE_TIMES_S)
    colors = plt.cm.viridis(np.linspace(0.0, 1.0, len(indices)))
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    for idx, t, color in zip(indices, PROFILE_TIMES_S, colors, strict=True):
        axes[0].plot(radii_cm, temperature[idx], color=color, label=f"{t} s")
        axes[1].plot(radii_cm, moisture[idx], color=color, label=f"{t} s")
    axes[0].set_title("Radial temperature profiles")
    axes[0].set_xlabel("Distance from centre (cm)")
    axes[0].set_ylabel("Temperature (deg C)")
    axes[1].set_title("Radial dry-basis moisture profiles")
    axes[1].set_xlabel("Distance from centre (cm)")
    axes[1].set_ylabel("Moisture (kg/kg)")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(ncol=2, fontsize=8, frameon=False)
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/problem_a_raw_oven_conditions_v01.xlsx"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("outputs"))
    parser.add_argument(
        "--final-intervals",
        type=int,
        default=2560,
        help="Number of radial intervals in the final solution.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_dir = args.output_root / "results"
    tables_dir = args.output_root / "tables"
    figures_dir = args.output_root / "figures"
    for directory in (results_dir, tables_dir, figures_dir):
        directory.mkdir(parents=True, exist_ok=True)

    air_time, air_temperature, air_moisture = load_air_conditions(args.input)
    output_time = np.arange(0, END_TIME_S + 1, dtype=float)

    if args.final_intervals < 80 or args.final_intervals % 4 != 0:
        raise ValueError("--final-intervals must be a multiple of 4 and at least 80.")
    grids = [
        args.final_intervals // 4,
        args.final_intervals // 2,
        args.final_intervals,
    ]
    solutions: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    sampled: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for intervals in grids:
        radius, temperature, moisture = solve_grid(
            intervals, air_time, air_temperature, air_moisture, output_time
        )
        solutions[intervals] = (radius, temperature, moisture)
        sampled[intervals] = (
            sample_radius(radius, temperature, TARGET_RADII_CM),
            sample_radius(radius, moisture, TARGET_RADII_CM),
        )

    final_radius, final_temperature_full, final_moisture_full = solutions[
        args.final_intervals
    ]
    final_temperature, final_moisture = sampled[args.final_intervals]

    write_wide_csv(
        results_dir / "problem_a_result_01_preheat_temperature_v01.csv",
        output_time[1:].astype(int),
        final_temperature[1:],
        TARGET_RADII_CM,
    )
    write_wide_csv(
        results_dir / "problem_a_result_02_preheat_moisture_v01.csv",
        output_time[1:].astype(int),
        final_moisture[1:],
        TARGET_RADII_CM,
    )
    key_table = make_key_table(
        tables_dir, output_time, final_temperature, final_moisture
    )
    plot_profiles(
        figures_dir / "problem_a_figure_01_preheat_profiles_v01.png",
        output_time,
        TARGET_RADII_CM,
        final_temperature,
        final_moisture,
    )

    convergence = []
    key_time_mask = np.isin(output_time, TARGET_TIMES_S)
    for coarse, fine in zip(grids[:-1], grids[1:], strict=True):
        coarse_t, coarse_c = sampled[coarse]
        fine_t, fine_c = sampled[fine]
        convergence.append(
            {
                "coarse_intervals": coarse,
                "fine_intervals": fine,
                "max_abs_temperature_c": float(np.max(np.abs(fine_t - coarse_t))),
                "max_abs_moisture_kg_per_kg": float(np.max(np.abs(fine_c - coarse_c))),
                "key_time_max_abs_temperature_c": float(
                    np.max(np.abs(fine_t[key_time_mask] - coarse_t[key_time_mask]))
                ),
                "key_time_max_abs_moisture_kg_per_kg": float(
                    np.max(np.abs(fine_c[key_time_mask] - coarse_c[key_time_mask]))
                ),
            }
        )

    avg_t = radial_average(final_radius, final_temperature_full)
    avg_c = radial_average(final_radius, final_moisture_full)
    air_t_each_second = np.interp(output_time, air_time, air_temperature)
    air_c_each_second = np.interp(output_time, air_time, air_moisture)
    predicted_t_change = np.trapezoid(
        2.0 * H * (air_t_each_second - final_temperature_full[:, -1])
        / (RHO * CP * RADIUS_M),
        output_time,
    )
    predicted_c_change = np.trapezoid(
        2.0 * HM * (air_c_each_second - final_moisture_full[:, -1]) / RADIUS_M,
        output_time,
    )
    balance = {
        "temperature_average_change_c": float(avg_t[-1] - avg_t[0]),
        "temperature_boundary_integral_c": float(predicted_t_change),
        "temperature_balance_abs_error_c": float(
            abs((avg_t[-1] - avg_t[0]) - predicted_t_change)
        ),
        "moisture_average_change_kg_per_kg": float(avg_c[-1] - avg_c[0]),
        "moisture_boundary_integral_kg_per_kg": float(predicted_c_change),
        "moisture_balance_abs_error_kg_per_kg": float(
            abs((avg_c[-1] - avg_c[0]) - predicted_c_change)
        ),
    }

    diagnostics = {
        "model": "one-dimensional radial cylindrical heat and moisture transfer",
        "numerical_method": "node-centred conservative finite volume + SciPy BDF",
        "input": str(args.input),
        "time_step_output_s": 1,
        "target_radius_step_cm": 0.1,
        "internal_radial_intervals": args.final_intervals,
        "internal_dr_cm": 2.0 / args.final_intervals,
        "solver_rtol": 1.0e-8,
        "heat_biot_number": H * RADIUS_M / K,
        "initial_moisture_diffusivity_m2_per_s": float(
            moisture_diffusivity(np.array([INITIAL_C]))[0]
        ),
        "initial_mass_biot_number": float(
            HM * RADIUS_M / moisture_diffusivity(np.array([INITIAL_C]))[0]
        ),
        "convergence": convergence,
        "balance": balance,
        "physical_checks": {
            "temperature_min_c": float(final_temperature_full.min()),
            "temperature_max_c": float(final_temperature_full.max()),
            "moisture_min_kg_per_kg": float(final_moisture_full.min()),
            "moisture_max_kg_per_kg": float(final_moisture_full.max()),
            "surface_temperature_ge_centre_at_1800s": bool(
                final_temperature_full[-1, -1] >= final_temperature_full[-1, 0]
            ),
            "surface_moisture_le_centre_at_1800s": bool(
                final_moisture_full[-1, -1] <= final_moisture_full[-1, 0]
            ),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    diagnostics_path = results_dir / "problem_a_result_03_preheat_diagnostics_v01.json"
    diagnostics_path.write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Key values (rounded only for display):")
    print(key_table.round({"temperature_c": 4, "moisture_kg_per_kg": 4}).to_string(index=False))
    print("\nConvergence:")
    print(pd.DataFrame(convergence).to_string(index=False))
    print("\nBalance:")
    print(json.dumps(balance, ensure_ascii=False, indent=2))
    print(f"\nDiagnostics written to {diagnostics_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
