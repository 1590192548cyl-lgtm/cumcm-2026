"""Validate the immutable Problem A input workbooks before model execution."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config/problem_a_config_v01.json"


def _load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _check(condition: bool, message: str, checks: list[str]) -> None:
    if not condition:
        raise ValueError(message)
    checks.append(message)


def main() -> None:
    config = _load_config()
    air_path = REPO_ROOT / config["paths"]["air_conditions"]
    radius_path = REPO_ROOT / config["paths"]["radius_history"]
    checks: list[str] = []

    _check(air_path.exists(), "air-condition workbook exists", checks)
    _check(radius_path.exists(), "radius-history workbook exists", checks)

    air = pd.read_excel(air_path)
    radius = pd.read_excel(radius_path)
    _check(list(air.columns[:3]) == ["时间", "温度", "水分浓度"], "air-condition headers match", checks)
    _check(list(radius.columns[:2]) == ["时间", "半径"], "radius-history headers match", checks)
    _check(air.shape == (241, 3), "air-condition table has 241 observations", checks)
    _check(radius.shape == (145, 2), "radius-history table has 145 observations", checks)

    air_values = air.iloc[:, :3].apply(pd.to_numeric, errors="raise").to_numpy(float)
    radius_values = radius.iloc[:, :2].apply(pd.to_numeric, errors="raise").to_numpy(float)
    _check(np.isfinite(air_values).all(), "air-condition values are finite", checks)
    _check(np.isfinite(radius_values).all(), "radius-history values are finite", checks)
    _check(np.array_equal(air_values[:, 0], np.arange(0, 14_400 + 60, 60)), "air timeline is 0-14400 s by 60 s", checks)
    _check(np.array_equal(radius_values[:, 0], np.arange(0, 259_200 + 1800, 1800)), "radius timeline is 0-259200 s by 1800 s", checks)
    _check((air_values[:, 1] > 0).all(), "air temperatures are positive", checks)
    _check((air_values[:, 2] >= 0).all(), "air moisture values are nonnegative", checks)
    _check((radius_values[:, 1] > 0).all(), "radius values are positive", checks)
    _check((np.diff(radius_values[:, 1]) <= 1.0e-12).all(), "radius is nonincreasing", checks)
    _check(abs(radius_values[0, 1] - 2.0) < 1.0e-12, "initial radius is 2 cm", checks)

    report = {
        "status": "pass",
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "check_count": len(checks),
        "checks": checks,
        "air_conditions": {
            "rows": int(len(air)),
            "time_min_s": float(air_values[0, 0]),
            "time_max_s": float(air_values[-1, 0]),
            "final_temperature_c": float(air_values[-1, 1]),
            "final_moisture_kg_per_kg": float(air_values[-1, 2])
        },
        "radius_history": {
            "rows": int(len(radius)),
            "time_min_s": float(radius_values[0, 0]),
            "time_max_s": float(radius_values[-1, 0]),
            "initial_radius_cm": float(radius_values[0, 1]),
            "final_radius_cm": float(radius_values[-1, 1])
        }
    }
    output_path = REPO_ROOT / "outputs/results/problem_a_result_00_input_validation_v01.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS: {len(checks)} Problem A input checks")
    print(output_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
