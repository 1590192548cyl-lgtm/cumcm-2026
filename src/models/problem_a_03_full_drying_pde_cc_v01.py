"""Solve Problem A questions 2--4 with variable properties and shrinkage.

Questions 2 and 3 use Appendix 3 material correlations on a fixed cylinder.
Question 4 uses Appendix 4 correlations and the measured time-varying radius in
attachment 2. The shrinking-domain model uses a normalized material coordinate,
so grid points follow material points while the physical radius changes.

All input and output paths are relative to the project root. Raw inputs are read
only. Numerical outputs are stored as CSV/JSON/PNG; the companion JavaScript
exporter creates the four required XLSX workbooks.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.integrate import solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.sparse import lil_matrix


INITIAL_T_C = 28.0
INITIAL_C = 2.55
INITIAL_RADIUS_M = 0.02
H = 25.0
HM = 8.0e-7
AIR_DATA_END_S = 14_400
Q2_END_S = 10_800
MAX_DRYING_TIME_S = 259_200
DRYING_THRESHOLD = 0.15
DISPLAY_ROUNDING_THRESHOLD = 0.14995
# The output must remain below the four-decimal display threshold after allowing
# for the largest observed coarse/fine spatial discrepancy (about 2.7e-5).
DISCRETIZATION_MARGIN = 3.0e-5
DISPLAY_SAFE_THRESHOLD = DISPLAY_ROUNDING_THRESHOLD - DISCRETIZATION_MARGIN
Q2_TABLE_TIMES_S = np.arange(1800, 10_800 + 1, 1800)
TABLE_RADII_CM = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
FIXED_OUTPUT_RADII_CM = np.arange(0.0, 2.0 + 1.0e-12, 0.1)
SHRINK_OUTPUT_RADII_CM = np.arange(0.0, 1.9 + 1.0e-12, 0.1)


@dataclass(frozen=True)
class MaterialModel:
    name: str
    rho: Callable[[np.ndarray], np.ndarray]
    cp: Callable[[np.ndarray], np.ndarray]
    conductivity: Callable[[np.ndarray], np.ndarray]
    diffusivity: Callable[[np.ndarray, np.ndarray], np.ndarray]


def appendix3_model() -> MaterialModel:
    return MaterialModel(
        name="appendix_3_fixed_radius",
        rho=lambda c: 650.0 + 128.0 * c,
        cp=lambda c: 1450.0 + 2736.0 * c / (c + 1.0),
        conductivity=lambda c: 0.21 + 0.38 * c / (c + 1.0),
        diffusivity=lambda c, t_k: 2.4e-3
        * np.exp(-0.45 / np.maximum(c, 1.0e-9))
        * np.exp(-3850.0 / t_k),
    )


def appendix4_model() -> MaterialModel:
    return MaterialModel(
        name="appendix_4_shrinking_radius",
        rho=lambda c: 760.0 + 90.0 * c,
        cp=lambda c: 1850.0 + 2150.0 * c / (c + 1.0),
        conductivity=lambda c: 0.12 + 0.20 * c / (c + 1.0),
        diffusivity=lambda c, t_k: 4.2e-4
        * np.exp(-0.30 / np.maximum(c, 1.0e-9))
        * np.exp(-3850.0 / t_k),
    )


def read_numeric_excel(path: Path, expected_columns: int) -> np.ndarray:
    frame = pd.read_excel(path, sheet_name=0)
    if frame.shape[1] < expected_columns:
        raise ValueError(f"{path} does not contain {expected_columns} columns.")
    values = (
        frame.iloc[:, :expected_columns]
        .apply(pd.to_numeric, errors="raise")
        .to_numpy(float)
    )
    if np.any(np.diff(values[:, 0]) <= 0):
        raise ValueError(f"Time values in {path} must be strictly increasing.")
    return values


def build_jacobian_sparsity(n_nodes: int):
    """Block tridiagonal dependency pattern for coupled heat and moisture."""

    pattern = lil_matrix((2 * n_nodes, 2 * n_nodes), dtype=int)
    for i in range(n_nodes):
        neighbours = range(max(0, i - 1), min(n_nodes, i + 2))
        for row_offset in (0, n_nodes):
            for j in neighbours:
                pattern[row_offset + i, j] = 1
                pattern[row_offset + i, n_nodes + j] = 1
    return pattern.tocsr()


def harmonic_mean(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return 2.0 * left * right / np.maximum(left + right, 1.0e-30)


class RadialDryingSolver:
    def __init__(
        self,
        intervals: int,
        material: MaterialModel,
        air_data: np.ndarray,
        radius_time_s: np.ndarray | None = None,
        radius_m: np.ndarray | None = None,
        face_average: str = "arithmetic",
        radius_interpolation: str = "linear",
        air_extension_mode: str = "last",
        air_tail_start_s: float = 9000.0,
        air_smoothing_tau_s: float = 3600.0,
        rtol: float = 2.0e-7,
        atol_temperature: float = 1.0e-8,
        atol_moisture: float = 1.0e-9,
        max_step_s: float = 60.0,
    ) -> None:
        self.intervals = intervals
        self.n_nodes = intervals + 1
        self.material = material
        self.xi = np.linspace(0.0, 1.0, self.n_nodes)
        self.dxi = self.xi[1] - self.xi[0]
        self.air_time_s = air_data[:, 0]
        self.air_temperature_c = air_data[:, 1]
        self.air_moisture = air_data[:, 2]
        self.radius_time_s = radius_time_s
        self.radius_values_m = radius_m
        if face_average not in {"arithmetic", "harmonic"}:
            raise ValueError("face_average must be 'arithmetic' or 'harmonic'.")
        if radius_interpolation not in {"linear", "pchip"}:
            raise ValueError("radius_interpolation must be 'linear' or 'pchip'.")
        if air_extension_mode not in {"last", "tail_mean", "smooth_tail_mean"}:
            raise ValueError(
                "air_extension_mode must be 'last', 'tail_mean', or 'smooth_tail_mean'."
            )
        self.face_average = face_average
        self.radius_interpolation = radius_interpolation
        self.air_extension_mode = air_extension_mode
        self.air_tail_start_s = float(air_tail_start_s)
        self.air_smoothing_tau_s = float(air_smoothing_tau_s)
        self.rtol = float(rtol)
        self.atol_temperature = float(atol_temperature)
        self.atol_moisture = float(atol_moisture)
        self.max_step_s = float(max_step_s)
        tail = self.air_time_s >= self.air_tail_start_s
        if not np.any(tail):
            raise ValueError("air_tail_start_s leaves no observations for the tail mean.")
        self.air_tail_temperature_c = float(np.mean(self.air_temperature_c[tail]))
        self.air_tail_moisture = float(np.mean(self.air_moisture[tail]))
        self._radius_pchip = None
        if radius_time_s is not None and radius_m is not None and radius_interpolation == "pchip":
            self._radius_pchip = PchipInterpolator(
                radius_time_s, radius_m, extrapolate=False
            )
        self.jacobian_sparsity = build_jacobian_sparsity(self.n_nodes)

    def radius_at(self, time_s: float) -> float:
        if self.radius_time_s is None or self.radius_values_m is None:
            return INITIAL_RADIUS_M
        if self._radius_pchip is not None and time_s <= self.radius_time_s[-1]:
            return float(self._radius_pchip(time_s))
        return float(
            np.interp(time_s, self.radius_time_s, self.radius_values_m)
        )

    def air_at(self, time_s: float) -> tuple[float, float]:
        if time_s <= self.air_time_s[-1] or self.air_extension_mode == "last":
            return (
                float(np.interp(time_s, self.air_time_s, self.air_temperature_c)),
                float(np.interp(time_s, self.air_time_s, self.air_moisture)),
            )
        if self.air_extension_mode == "tail_mean":
            return self.air_tail_temperature_c, self.air_tail_moisture
        weight = np.exp(
            -(time_s - self.air_time_s[-1]) / max(self.air_smoothing_tau_s, 1.0)
        )
        return (
            self.air_tail_temperature_c
            + weight * (self.air_temperature_c[-1] - self.air_tail_temperature_c),
            self.air_tail_moisture
            + weight * (self.air_moisture[-1] - self.air_tail_moisture),
        )

    def rhs(self, time_s: float, state: np.ndarray) -> np.ndarray:
        temperature_c = state[: self.n_nodes]
        moisture = state[self.n_nodes :]
        temperature_k = temperature_c + 273.15
        radius = self.radius_at(time_s)
        radial_nodes = self.xi * radius
        radial_faces = np.empty(self.n_nodes + 1)
        radial_faces[0] = 0.0
        radial_faces[-1] = radius
        radial_faces[1:-1] = 0.5 * (radial_nodes[:-1] + radial_nodes[1:])
        control_volume = 0.5 * (radial_faces[1:] ** 2 - radial_faces[:-1] ** 2)
        dr = radius * self.dxi
        air_temperature_c, air_moisture = self.air_at(time_s)

        rho = self.material.rho(moisture)
        cp = self.material.cp(moisture)
        conductivity = self.material.conductivity(moisture)
        if self.face_average == "harmonic":
            face_conductivity = harmonic_mean(conductivity[:-1], conductivity[1:])
        else:
            face_conductivity = 0.5 * (conductivity[:-1] + conductivity[1:])

        heat_flux_like = np.empty(self.n_nodes + 1)
        heat_flux_like[0] = 0.0
        heat_flux_like[1:-1] = face_conductivity * np.diff(temperature_c) / dr
        heat_flux_like[-1] = H * (air_temperature_c - temperature_c[-1])
        temperature_rate = (
            radial_faces[1:] * heat_flux_like[1:]
            - radial_faces[:-1] * heat_flux_like[:-1]
        ) / (rho * cp * control_volume)

        diffusivity = self.material.diffusivity(moisture, temperature_k)
        if self.face_average == "harmonic":
            face_diffusivity = harmonic_mean(diffusivity[:-1], diffusivity[1:])
        else:
            face_diffusivity = 0.5 * (diffusivity[:-1] + diffusivity[1:])
        moisture_flux_like = np.empty(self.n_nodes + 1)
        moisture_flux_like[0] = 0.0
        moisture_flux_like[1:-1] = face_diffusivity * np.diff(moisture) / dr
        moisture_flux_like[-1] = HM * (air_moisture - moisture[-1])
        moisture_rate = (
            radial_faces[1:] * moisture_flux_like[1:]
            - radial_faces[:-1] * moisture_flux_like[:-1]
        ) / control_volume
        return np.concatenate([temperature_rate, moisture_rate])

    def initial_state(self) -> np.ndarray:
        return np.concatenate(
            [
                np.full(self.n_nodes, INITIAL_T_C),
                np.full(self.n_nodes, INITIAL_C),
            ]
        )

    def sample_state(
        self,
        time_s: float,
        state: np.ndarray,
        fixed_radii_cm: np.ndarray,
        include_surface: bool = False,
    ) -> tuple[np.ndarray, np.ndarray]:
        radius_m = self.radius_at(time_s)
        node_radius_m = self.xi * radius_m
        target_radius_m = fixed_radii_cm / 100.0
        temperature = state[: self.n_nodes]
        moisture = state[self.n_nodes :]
        sampled_temperature = np.full(target_radius_m.shape, np.nan)
        sampled_moisture = np.full(target_radius_m.shape, np.nan)
        valid = target_radius_m <= radius_m + 1.0e-12
        sampled_temperature[valid] = np.interp(
            target_radius_m[valid], node_radius_m, temperature
        )
        sampled_moisture[valid] = np.interp(
            target_radius_m[valid], node_radius_m, moisture
        )
        if include_surface:
            sampled_temperature = np.append(sampled_temperature, temperature[-1])
            sampled_moisture = np.append(sampled_moisture, moisture[-1])
        return sampled_temperature, sampled_moisture

    def solve_sampled(
        self,
        end_time_s: int,
        output_step_s: int,
        fixed_radii_cm: np.ndarray,
        include_surface: bool = False,
        stop_at_dry: bool = False,
        stop_threshold: float = DRYING_THRESHOLD,
        chunk_s: int = 1800,
    ) -> dict[str, np.ndarray | float]:
        state = self.initial_state()
        collected_time: list[float] = [0.0]
        t0, c0 = self.sample_state(0.0, state, fixed_radii_cm, include_surface)
        collected_temperature: list[np.ndarray] = [t0]
        collected_moisture: list[np.ndarray] = [c0]
        drying_time_s: float | None = None
        threshold_time_s: float | None = None
        final_dense_solution = None

        chunk_start = 0
        while chunk_start < end_time_s:
            chunk_end = min(chunk_start + chunk_s, end_time_s)
            output_times = np.arange(
                chunk_start + output_step_s,
                chunk_end + 1,
                output_step_s,
                dtype=float,
            )
            if output_times.size == 0 or output_times[-1] != chunk_end:
                output_times = np.append(output_times, float(chunk_end))
            atol = np.concatenate(
                [
                    np.full(self.n_nodes, self.atol_temperature),
                    np.full(self.n_nodes, self.atol_moisture),
                ]
            )
            def threshold_event(time_s, sampled_state):
                return sampled_state[self.n_nodes] - DRYING_THRESHOLD

            threshold_event.direction = -1
            threshold_event.terminal = False

            def stop_event(time_s, sampled_state):
                return sampled_state[self.n_nodes] - stop_threshold

            stop_event.direction = -1
            stop_event.terminal = False
            events = [threshold_event]
            if abs(stop_threshold - DRYING_THRESHOLD) > 1.0e-12:
                events.append(stop_event)

            solution = solve_ivp(
                self.rhs,
                (float(chunk_start), float(chunk_end)),
                state,
                method="BDF",
                t_eval=output_times,
                rtol=self.rtol,
                atol=atol,
                jac_sparsity=self.jacobian_sparsity,
                events=events if stop_at_dry else None,
                dense_output=stop_at_dry,
                max_step=self.max_step_s,
            )
            if not solution.success:
                raise RuntimeError(f"Solver failed: {solution.message}")
            final_dense_solution = solution.sol

            for time_s, sampled_state in zip(
                solution.t, solution.y.T, strict=True
            ):
                sampled_temperature, sampled_moisture = self.sample_state(
                    float(time_s),
                    sampled_state,
                    fixed_radii_cm,
                    include_surface,
                )
                collected_time.append(float(time_s))
                collected_temperature.append(sampled_temperature)
                collected_moisture.append(sampled_moisture)
            if stop_at_dry and solution.t_events:
                if threshold_time_s is None and solution.t_events[0].size:
                    threshold_time_s = float(solution.t_events[0][0])
                stop_events = solution.t_events[-1]
                if stop_events.size:
                    drying_time_s = float(stop_events[0])

            state = solution.y[:, -1]
            chunk_start = chunk_end
            if drying_time_s is not None:
                break

        time = np.asarray(collected_time)
        temperature = np.vstack(collected_temperature)
        moisture = np.vstack(collected_moisture)
        if drying_time_s is not None:
            operational_end_s = int(np.ceil(drying_time_s / output_step_s) * output_step_s)
            keep = time <= operational_end_s + 1.0e-9
            time = time[keep]
            temperature = temperature[keep]
            moisture = moisture[keep]
            if final_dense_solution is not None:
                state = np.asarray(final_dense_solution(float(operational_end_s)))
        else:
            operational_end_s = int(time[-1])
        return {
            "time_s": time,
            "temperature_c": temperature,
            "moisture": moisture,
            "drying_time_s": float(drying_time_s) if drying_time_s is not None else np.nan,
            "threshold_time_s": (
                float(threshold_time_s) if threshold_time_s is not None else np.nan
            ),
            "operational_end_s": float(operational_end_s),
            "stopping_threshold": float(stop_threshold),
            "display_rounding_threshold": float(DISPLAY_ROUNDING_THRESHOLD),
            "discretization_margin": float(DISCRETIZATION_MARGIN),
            "final_state": state,
        }


def write_wide_csv(
    path: Path,
    time_s: np.ndarray,
    values: np.ndarray,
    column_labels: list[str],
) -> None:
    frame = pd.DataFrame(values, columns=column_labels)
    frame.insert(0, "time_s", time_s.astype(int))
    frame.to_csv(path, index=False, float_format="%.8f")


def interpolate_time(
    time_s: np.ndarray, values: np.ndarray, target_time_s: np.ndarray
) -> np.ndarray:
    columns = [np.interp(target_time_s, time_s, values[:, j]) for j in range(values.shape[1])]
    return np.column_stack(columns)


def first_threshold_crossing_time(
    time_s: np.ndarray,
    centre_moisture: np.ndarray,
    threshold: float,
) -> float:
    """Linearly interpolate the first downward crossing of a moisture threshold."""

    crossing = np.flatnonzero(centre_moisture <= threshold)
    if crossing.size == 0:
        return float("nan")
    current = int(crossing[0])
    if current == 0:
        return float(time_s[0])
    previous = current - 1
    numerator = centre_moisture[previous] - threshold
    denominator = max(
        centre_moisture[previous] - centre_moisture[current], 1.0e-15
    )
    return float(
        time_s[previous]
        + numerator / denominator * (time_s[current] - time_s[previous])
    )


def make_key_table(
    time_s: np.ndarray,
    values: np.ndarray,
    target_time_s: np.ndarray,
    radii_cm: np.ndarray,
    value_name: str,
) -> pd.DataFrame:
    target_values = interpolate_time(time_s, values, target_time_s)
    rows: list[dict[str, float]] = []
    for row_index, time in enumerate(target_time_s):
        for column_index, radius in enumerate(radii_cm):
            rows.append(
                {
                    "time_s": float(time),
                    "time_h": float(time / 3600.0),
                    "radius_cm": float(radius),
                    value_name: float(target_values[row_index, column_index]),
                }
            )
    return pd.DataFrame(rows)


def plot_q2_profiles(
    path: Path,
    q2: dict[str, np.ndarray | float],
) -> None:
    time_s = np.asarray(q2["time_s"])
    temperature = np.asarray(q2["temperature_c"])
    moisture = np.asarray(q2["moisture"])
    selected_temperature = interpolate_time(time_s, temperature, Q2_TABLE_TIMES_S)
    selected_moisture = interpolate_time(time_s, moisture, Q2_TABLE_TIMES_S)
    colors = plt.cm.viridis(np.linspace(0.05, 0.95, Q2_TABLE_TIMES_S.size))
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    for row, time_s_value, color in zip(
        range(Q2_TABLE_TIMES_S.size), Q2_TABLE_TIMES_S, colors, strict=True
    ):
        label = f"{time_s_value / 3600:.1f} h"
        axes[0].plot(FIXED_OUTPUT_RADII_CM, selected_temperature[row], color=color, label=label)
        axes[1].plot(FIXED_OUTPUT_RADII_CM, selected_moisture[row], color=color, label=label)
    axes[0].set_title("Temperature profiles during the first 3 h")
    axes[0].set_xlabel("Distance from centre (cm)")
    axes[0].set_ylabel("Temperature (deg C)")
    axes[1].set_title("Moisture profiles during the first 3 h")
    axes[1].set_xlabel("Distance from centre (cm)")
    axes[1].set_ylabel("Dry-basis moisture (kg/kg)")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(frameon=False, fontsize=8, ncol=2)
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_drying_comparison(
    path: Path,
    q3: dict[str, np.ndarray | float],
    q4: dict[str, np.ndarray | float],
    radius_data: np.ndarray,
) -> None:
    q3_time = np.asarray(q3["time_s"])
    q4_time = np.asarray(q4["time_s"])
    q3_moisture = np.asarray(q3["moisture"])
    q4_moisture = np.asarray(q4["moisture"])
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    axes[0].plot(q3_time / 3600.0, q3_moisture[:, 0], label="Fixed radius: centre")
    axes[0].plot(q3_time / 3600.0, q3_moisture[:, -1], label="Fixed radius: surface")
    axes[0].plot(q4_time / 3600.0, q4_moisture[:, 0], label="Shrinking: centre")
    axes[0].plot(q4_time / 3600.0, q4_moisture[:, -1], label="Shrinking: surface")
    axes[0].axhline(DRYING_THRESHOLD, color="#B91C1C", linestyle="--", label="Threshold 0.15")
    axes[0].set_title("Drying trajectories")
    axes[0].set_xlabel("Time (h)")
    axes[0].set_ylabel("Dry-basis moisture (kg/kg)")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)

    axes[1].plot(radius_data[:, 0] / 3600.0, radius_data[:, 1], color="#2F855A")
    axes[1].set_title("Measured radius during drying")
    axes[1].set_xlabel("Time (h)")
    axes[1].set_ylabel("Radius (cm)")
    axes[1].grid(alpha=0.25)
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


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
    parser.add_argument("--output-root", type=Path, default=Path("outputs"))
    parser.add_argument("--q2-intervals", type=int, default=1280)
    parser.add_argument("--drying-intervals", type=int, default=2560)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for value in (args.q2_intervals, args.drying_intervals):
        if value < 80 or value % 20 != 0:
            raise ValueError("Grid intervals must be multiples of 20 and at least 80.")

    results_dir = args.output_root / "results"
    tables_dir = args.output_root / "tables"
    figures_dir = args.output_root / "figures"
    for directory in (results_dir, tables_dir, figures_dir):
        directory.mkdir(parents=True, exist_ok=True)

    air_data = read_numeric_excel(args.air_input, 3)
    radius_data_cm = read_numeric_excel(args.radius_input, 2)
    radius_time_s = radius_data_cm[:, 0]
    radius_m = radius_data_cm[:, 1] / 100.0
    if air_data[-1, 0] != AIR_DATA_END_S:
        raise ValueError("Attachment 1 must end at 14400 s for the stated extension rule.")

    fixed_model = appendix3_model()
    q2_solver = RadialDryingSolver(args.q2_intervals, fixed_model, air_data)
    q2 = q2_solver.solve_sampled(
        Q2_END_S,
        1,
        FIXED_OUTPUT_RADII_CM,
        chunk_s=600,
    )
    q2_time = np.asarray(q2["time_s"])[1:]
    q2_temperature = np.asarray(q2["temperature_c"])[1:]
    q2_moisture = np.asarray(q2["moisture"])[1:]
    fixed_labels = [f"r_{radius:.1f}_cm" for radius in FIXED_OUTPUT_RADII_CM]
    write_wide_csv(
        results_dir / "problem_a_result_05_q2_temperature_v01.csv",
        q2_time,
        q2_temperature,
        fixed_labels,
    )
    write_wide_csv(
        results_dir / "problem_a_result_06_q2_moisture_v01.csv",
        q2_time,
        q2_moisture,
        fixed_labels,
    )

    q2_key_temperature = make_key_table(
        q2_time,
        q2_temperature[:, ::5],
        Q2_TABLE_TIMES_S,
        TABLE_RADII_CM,
        "temperature_c",
    )
    q2_key_moisture = make_key_table(
        q2_time,
        q2_moisture[:, ::5],
        Q2_TABLE_TIMES_S,
        TABLE_RADII_CM,
        "moisture_kg_per_kg",
    )
    q2_key = q2_key_temperature.merge(
        q2_key_moisture,
        on=["time_s", "time_h", "radius_cm"],
        validate="one_to_one",
    )
    q2_key.to_csv(
        tables_dir / "problem_a_table_02_q2_key_values_v01.csv",
        index=False,
        float_format="%.8f",
    )
    plot_q2_profiles(
        figures_dir / "problem_a_figure_02_q2_profiles_v01.png",
        q2,
    )

    q3_solver = RadialDryingSolver(args.drying_intervals, fixed_model, air_data)
    q3 = q3_solver.solve_sampled(
        MAX_DRYING_TIME_S,
        60,
        FIXED_OUTPUT_RADII_CM,
        stop_at_dry=True,
        stop_threshold=DISPLAY_SAFE_THRESHOLD,
        chunk_s=3600,
    )
    if not np.isfinite(q3["drying_time_s"]):
        raise RuntimeError("Question 3 did not reach the drying threshold within 72 h.")
    q3_time = np.asarray(q3["time_s"])[1:]
    q3_moisture = np.asarray(q3["moisture"])[1:]
    q3_threshold_time_s = float(q3["threshold_time_s"])
    write_wide_csv(
        results_dir / "problem_a_result_07_q3_moisture_v01.csv",
        q3_time,
        q3_moisture,
        fixed_labels,
    )

    shrinking_model = appendix4_model()
    q4_solver = RadialDryingSolver(
        args.drying_intervals,
        shrinking_model,
        air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
    )
    q4 = q4_solver.solve_sampled(
        MAX_DRYING_TIME_S,
        60,
        SHRINK_OUTPUT_RADII_CM,
        include_surface=True,
        stop_at_dry=True,
        stop_threshold=DISPLAY_SAFE_THRESHOLD,
        chunk_s=1800,
    )
    if not np.isfinite(q4["drying_time_s"]):
        raise RuntimeError("Question 4 did not reach the drying threshold within 72 h.")
    q4_time = np.asarray(q4["time_s"])[1:]
    q4_moisture = np.asarray(q4["moisture"])[1:]
    q4_threshold_time_s = float(q4["threshold_time_s"])
    shrink_labels = [f"r_{radius:.1f}_cm" for radius in SHRINK_OUTPUT_RADII_CM] + [
        "surface"
    ]
    write_wide_csv(
        results_dir / "problem_a_result_08_q4_moisture_v01.csv",
        q4_time,
        q4_moisture,
        shrink_labels,
    )

    def six_hour_times(end_s: float) -> np.ndarray:
        regular = np.arange(21_600, end_s, 21_600, dtype=float)
        return np.append(regular, end_s)

    q3_table_times = six_hour_times(float(q3["operational_end_s"]))
    q3_table_values = interpolate_time(q3_time, q3_moisture[:, ::5], q3_table_times)
    pd.DataFrame(
        np.column_stack([q3_table_times / 3600.0, q3_table_values]),
        columns=["time_h"] + [f"r_{r:.1f}_cm" for r in TABLE_RADII_CM],
    ).to_csv(
        tables_dir / "problem_a_table_03_q3_six_hour_values_v01.csv",
        index=False,
        float_format="%.8f",
    )

    q4_table_times = six_hour_times(float(q4["operational_end_s"]))
    q4_all_values = interpolate_time(q4_time, q4_moisture, q4_table_times)
    q4_columns = [0, 5, 10, 15, -1]
    pd.DataFrame(
        np.column_stack([q4_table_times / 3600.0, q4_all_values[:, q4_columns]]),
        columns=["time_h", "r_0.0_cm", "r_0.5_cm", "r_1.0_cm", "r_1.5_cm", "surface"],
    ).to_csv(
        tables_dir / "problem_a_table_04_q4_six_hour_values_v01.csv",
        index=False,
        float_format="%.8f",
    )

    plot_drying_comparison(
        figures_dir / "problem_a_figure_03_drying_comparison_v01.png",
        q3,
        q4,
        radius_data_cm,
    )

    drying_coarse_intervals = args.drying_intervals // 2
    q3_coarse_solver = RadialDryingSolver(
        drying_coarse_intervals, fixed_model, air_data
    )
    q3_coarse = q3_coarse_solver.solve_sampled(
        MAX_DRYING_TIME_S,
        60,
        TABLE_RADII_CM,
        stop_at_dry=True,
        stop_threshold=DISPLAY_SAFE_THRESHOLD,
        chunk_s=3600,
    )
    q4_coarse_solver = RadialDryingSolver(
        drying_coarse_intervals,
        shrinking_model,
        air_data,
        radius_time_s=radius_time_s,
        radius_m=radius_m,
    )
    q4_coarse = q4_coarse_solver.solve_sampled(
        MAX_DRYING_TIME_S,
        60,
        SHRINK_OUTPUT_RADII_CM,
        include_surface=True,
        stop_at_dry=True,
        stop_threshold=DISPLAY_SAFE_THRESHOLD,
        chunk_s=1800,
    )
    q3_coarse_threshold_time_s = float(q3_coarse["threshold_time_s"])
    q4_coarse_threshold_time_s = float(q4_coarse["threshold_time_s"])
    q3_common_times = np.arange(
        21_600,
        min(float(q3["operational_end_s"]), float(q3_coarse["operational_end_s"]))
        + 1,
        21_600,
        dtype=float,
    )
    q4_common_times = np.arange(
        21_600,
        min(float(q4["operational_end_s"]), float(q4_coarse["operational_end_s"]))
        + 1,
        21_600,
        dtype=float,
    )
    q3_fine_check = interpolate_time(
        np.asarray(q3["time_s"]),
        np.asarray(q3["moisture"])[:, ::5],
        q3_common_times,
    )
    q3_coarse_check = interpolate_time(
        np.asarray(q3_coarse["time_s"]),
        np.asarray(q3_coarse["moisture"]),
        q3_common_times,
    )
    q4_fine_check = interpolate_time(
        np.asarray(q4["time_s"]),
        np.asarray(q4["moisture"]),
        q4_common_times,
    )
    q4_coarse_check = interpolate_time(
        np.asarray(q4_coarse["time_s"]),
        np.asarray(q4_coarse["moisture"]),
        q4_common_times,
    )

    q2_coarse_solver = RadialDryingSolver(args.q2_intervals // 2, fixed_model, air_data)
    q2_coarse = q2_coarse_solver.solve_sampled(
        Q2_END_S,
        1800,
        TABLE_RADII_CM,
        chunk_s=1800,
    )
    q2_fine_key_t = interpolate_time(
        np.asarray(q2["time_s"]), np.asarray(q2["temperature_c"])[:, ::5], Q2_TABLE_TIMES_S
    )
    q2_fine_key_c = interpolate_time(
        np.asarray(q2["time_s"]), np.asarray(q2["moisture"])[:, ::5], Q2_TABLE_TIMES_S
    )
    q2_coarse_t = interpolate_time(
        np.asarray(q2_coarse["time_s"]), np.asarray(q2_coarse["temperature_c"]), Q2_TABLE_TIMES_S
    )
    q2_coarse_c = interpolate_time(
        np.asarray(q2_coarse["time_s"]), np.asarray(q2_coarse["moisture"]), Q2_TABLE_TIMES_S
    )

    diagnostics = {
        "air_extension_after_14400_s": {
            "method": "constant continuation of final observation",
            "temperature_c": float(air_data[-1, 1]),
            "moisture_kg_per_kg": float(air_data[-1, 2]),
        },
        "boundary_coefficients_retained_from_appendix_2": {
            "h_w_per_m2_k": H,
            "hm_m_per_s": HM,
        },
        "question_2": {
            "grid_intervals": args.q2_intervals,
            "grid_dr_cm": 2.0 / args.q2_intervals,
            "coarse_grid_intervals": args.q2_intervals // 2,
            "key_time_max_abs_temperature_difference_c": float(
                np.nanmax(np.abs(q2_fine_key_t - q2_coarse_t))
            ),
            "key_time_max_abs_moisture_difference_kg_per_kg": float(
                np.nanmax(np.abs(q2_fine_key_c - q2_coarse_c))
            ),
        },
        "question_3": {
            "grid_intervals": args.drying_intervals,
            "coarse_grid_intervals": drying_coarse_intervals,
            "drying_time_s_interpolated": q3_threshold_time_s,
            "drying_time_h_interpolated": q3_threshold_time_s / 3600.0,
            "display_safe_threshold_kg_per_kg": DISPLAY_SAFE_THRESHOLD,
            "display_safe_time_s_interpolated": float(q3["drying_time_s"]),
            "display_safe_time_h_interpolated": float(q3["drying_time_s"] / 3600.0),
            "coarse_drying_time_h_interpolated": float(
                q3_coarse_threshold_time_s / 3600.0
            ),
            "drying_time_abs_difference_h": float(
                abs(q3_threshold_time_s - q3_coarse_threshold_time_s) / 3600.0
            ),
            "six_hour_max_abs_moisture_difference_kg_per_kg": float(
                np.nanmax(np.abs(q3_fine_check - q3_coarse_check))
            ),
            "operational_end_s": int(q3["operational_end_s"]),
            "operational_end_h": float(q3["operational_end_s"] / 3600.0),
            "maximum_moisture_at_operational_end": float(np.nanmax(q3_moisture[-1])),
        },
        "question_4": {
            "grid_intervals": args.drying_intervals,
            "coarse_grid_intervals": drying_coarse_intervals,
            "coordinate": "normalized material radius xi=r/R(t)",
            "drying_time_s_interpolated": q4_threshold_time_s,
            "drying_time_h_interpolated": q4_threshold_time_s / 3600.0,
            "display_safe_threshold_kg_per_kg": DISPLAY_SAFE_THRESHOLD,
            "display_safe_time_s_interpolated": float(q4["drying_time_s"]),
            "display_safe_time_h_interpolated": float(q4["drying_time_s"] / 3600.0),
            "coarse_drying_time_h_interpolated": float(
                q4_coarse_threshold_time_s / 3600.0
            ),
            "drying_time_abs_difference_h": float(
                abs(q4_threshold_time_s - q4_coarse_threshold_time_s) / 3600.0
            ),
            "six_hour_max_abs_moisture_difference_kg_per_kg": float(
                np.nanmax(np.abs(q4_fine_check - q4_coarse_check))
            ),
            "operational_end_s": int(q4["operational_end_s"]),
            "operational_end_h": float(q4["operational_end_s"] / 3600.0),
            "radius_at_operational_end_cm": float(
                np.interp(q4["operational_end_s"], radius_time_s, radius_data_cm[:, 1])
            ),
            "maximum_moisture_at_operational_end": float(np.nanmax(q4_moisture[-1])),
        },
        "physical_checks": {
            "q2_temperature_min_c": float(np.nanmin(q2_temperature)),
            "q2_temperature_max_c": float(np.nanmax(q2_temperature)),
            "q2_moisture_min": float(np.nanmin(q2_moisture)),
            "q2_moisture_max": float(np.nanmax(q2_moisture)),
            "q3_moisture_nonnegative": bool(np.nanmin(q3_moisture) >= 0.0),
            "q4_moisture_nonnegative": bool(np.nanmin(q4_moisture) >= 0.0),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    diagnostics_path = results_dir / "problem_a_result_09_full_drying_diagnostics_v01.json"
    diagnostics_path.write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Question 2 key values:")
    print(q2_key.round(4).to_string(index=False))
    print("\nDrying times:")
    print(
        json.dumps(
            {
                "q3_h": diagnostics["question_3"]["drying_time_h_interpolated"],
                "q3_operational_h": diagnostics["question_3"]["operational_end_h"],
                "q4_h": diagnostics["question_4"]["drying_time_h_interpolated"],
                "q4_operational_h": diagnostics["question_4"]["operational_end_h"],
            },
            indent=2,
        )
    )
    print("\nGrid check:")
    print(json.dumps(diagnostics["question_2"], indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
