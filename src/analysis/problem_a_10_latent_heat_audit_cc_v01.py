"""Audit whether a naive evaporative-latent-heat boundary term is identifiable.

This script does not replace the official model.  It evaluates the magnitude of
the latent-heat demand implied by the existing moisture boundary condition and
compares it with the convective heat supplied at the surface during Question 2.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AIR_FILE = ROOT / "data/raw/problem_a_raw_attachment_1_v01.xlsx"
TEMPERATURE_FILE = ROOT / "outputs/results/problem_a_result_05_q2_temperature_v01.csv"
MOISTURE_FILE = ROOT / "outputs/results/problem_a_result_06_q2_moisture_v01.csv"
TABLE_FILE = ROOT / "outputs/tables/problem_a_table_07_latent_heat_audit_v01.csv"
RESULT_FILE = ROOT / "outputs/results/problem_a_result_16_latent_heat_audit_v01.json"

HEAT_TRANSFER_COEFFICIENT = 25.0
MASS_TRANSFER_COEFFICIENT = 8.0e-7
LATENT_HEAT_DIAGNOSTIC = 2.4e6
KEY_TIMES_S = np.array([60, 600, 1200, 1800, 3600, 5400, 10800], dtype=float)


def main() -> None:
    temperature = pd.read_csv(TEMPERATURE_FILE)
    moisture = pd.read_csv(MOISTURE_FILE)
    air = pd.read_excel(AIR_FILE)
    if not np.array_equal(temperature["time_s"], moisture["time_s"]):
        raise ValueError("Question 2 temperature and moisture times do not match.")

    time_s = temperature["time_s"].to_numpy(float)
    air_time_s = air.iloc[:, 0].to_numpy(float)
    air_temperature_c = np.interp(time_s, air_time_s, air.iloc[:, 1].to_numpy(float))
    air_moisture = np.interp(time_s, air_time_s, air.iloc[:, 2].to_numpy(float))
    surface_temperature_c = temperature.iloc[:, -1].to_numpy(float)
    surface_moisture = moisture.iloc[:, -1].to_numpy(float)

    # C is dry-basis moisture, so wet bulk density cannot be used directly to
    # convert dC/dt into a water-mass flux.  rho_d = rho_wet/(1+C) is an explicit
    # diagnostic closure, not an additional official-model parameter.
    wet_bulk_density = 650.0 + 128.0 * surface_moisture
    dry_mass_density = wet_bulk_density / (1.0 + surface_moisture)
    moisture_driving_force = np.maximum(surface_moisture - air_moisture, 0.0)
    water_flux_demand = (
        dry_mass_density * MASS_TRANSFER_COEFFICIENT * moisture_driving_force
    )
    convective_heat_flux = HEAT_TRANSFER_COEFFICIENT * np.maximum(
        air_temperature_c - surface_temperature_c, 0.0
    )
    latent_heat_flux_demand = LATENT_HEAT_DIAGNOSTIC * water_flux_demand
    flux_ratio = latent_heat_flux_demand / np.maximum(convective_heat_flux, 1.0e-12)
    required_temperature_difference = (
        latent_heat_flux_demand / HEAT_TRANSFER_COEFFICIENT
    )
    available_temperature_difference = air_temperature_c - surface_temperature_c
    implied_balance_temperature_c = air_temperature_c - required_temperature_difference

    full = pd.DataFrame(
        {
            "time_s": time_s,
            "time_h": time_s / 3600.0,
            "air_temperature_c": air_temperature_c,
            "surface_temperature_c": surface_temperature_c,
            "air_moisture_kg_per_kg": air_moisture,
            "surface_moisture_kg_per_kg": surface_moisture,
            "diagnostic_dry_mass_density_kg_per_m3": dry_mass_density,
            "convective_heat_flux_w_per_m2": convective_heat_flux,
            "latent_heat_flux_demand_w_per_m2": latent_heat_flux_demand,
            "latent_to_convective_flux_ratio": flux_ratio,
            "available_temperature_difference_k": available_temperature_difference,
            "required_temperature_difference_k": required_temperature_difference,
            "instantaneous_balance_temperature_c": implied_balance_temperature_c,
        }
    )
    key_indices = [int(np.argmin(np.abs(time_s - value))) for value in KEY_TIMES_S]
    key = full.iloc[key_indices].copy()
    TABLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    key.to_csv(TABLE_FILE, index=False, float_format="%.8f")

    half_hour = key.loc[key["time_s"] == 1800].iloc[0]
    summary = {
        "scope": "diagnostic only; official model and official outputs unchanged",
        "diagnostic_assumptions": {
            "latent_heat_j_per_kg": LATENT_HEAT_DIAGNOSTIC,
            "dry_mass_density_relation": "rho_d = (650 + 128 C_s)/(1 + C_s)",
            "surface_water_flux_relation": "j_w = rho_d h_m max(C_s - C_air, 0)",
        },
        "question_2_first_3h": {
            "minimum_latent_to_convective_flux_ratio": float(np.min(flux_ratio)),
            "time_of_minimum_ratio_s": float(time_s[int(np.argmin(flux_ratio))]),
        },
        "at_1800_s": {
            "convective_heat_flux_w_per_m2": float(
                half_hour["convective_heat_flux_w_per_m2"]
            ),
            "latent_heat_flux_demand_w_per_m2": float(
                half_hour["latent_heat_flux_demand_w_per_m2"]
            ),
            "latent_to_convective_flux_ratio": float(
                half_hour["latent_to_convective_flux_ratio"]
            ),
            "available_temperature_difference_k": float(
                half_hour["available_temperature_difference_k"]
            ),
            "required_temperature_difference_k": float(
                half_hour["required_temperature_difference_k"]
            ),
            "instantaneous_balance_temperature_c": float(
                half_hour["instantaneous_balance_temperature_c"]
            ),
        },
        "decision": (
            "Do not insert the naive latent sink into the official model.  The supplied "
            "heat and mass boundary laws are not jointly energy-closed under this "
            "conversion.  A physically coupled replacement needs dry-matter density, "
            "a sorption/equilibrium relation, and energy-limited evaporation calibration."
        ),
    }
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
