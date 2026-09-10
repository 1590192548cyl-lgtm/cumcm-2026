"""Convert Problem C wide workbooks into canonical long-format model inputs."""

from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config/problem_c_config_v01.json"


def _load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _parse_clock(time_value: Any) -> tuple[int, int]:
    if isinstance(time_value, time):
        return time_value.hour, time_value.minute
    text = str(time_value).strip().removesuffix("+1")
    parsed = datetime.strptime(text, "%H:%M")
    return parsed.hour, parsed.minute


def _interval_end(date_value: pd.Timestamp, time_value: Any) -> pd.Timestamp:
    base = pd.Timestamp(date_value).normalize()
    hour, minute = _parse_clock(time_value)
    if hour == 0 and minute == 0:
        return base + pd.Timedelta(days=1)
    return base + pd.Timedelta(hours=hour, minutes=minute)


def _wide_daily_sheet(path: Path, sheet_name: str, value_name: str) -> pd.DataFrame:
    wide = pd.read_excel(path, sheet_name=sheet_name)
    date_column = wide.columns[0]
    long = wide.melt(id_vars=[date_column], var_name="time", value_name=value_name)
    long = long.rename(columns={date_column: "date"})
    long["date"] = pd.to_datetime(long["date"])
    long["interval_end"] = [
        _interval_end(date_value, time_value)
        for date_value, time_value in zip(long["date"], long["time"], strict=True)
    ]
    return long[["date", "interval_end", value_name]].sort_values("interval_end").reset_index(drop=True)


def _build_q1(config: dict[str, Any]) -> pd.DataFrame:
    source = REPO_ROOT / config["paths"]["attachment_1"]
    frame = pd.read_excel(source)
    frame.columns = ["time", "price_yuan_per_kwh", "load_kw", "pv_forecast_kw"]
    frame.insert(0, "step", range(1, len(frame) + 1))
    frame["interval_end_minute"] = frame["step"] * config["time_step_minutes"]
    frame["interval_start_minute"] = frame["interval_end_minute"] - config["time_step_minutes"]
    frame["duration_h"] = config["time_step_minutes"] / 60
    return frame[
        [
            "step",
            "interval_start_minute",
            "interval_end_minute",
            "duration_h",
            "price_yuan_per_kwh",
            "load_kw",
            "pv_forecast_kw",
        ]
    ]


def _build_actual_panel(config: dict[str, Any], q1: pd.DataFrame) -> pd.DataFrame:
    attachment_2 = REPO_ROOT / config["paths"]["attachment_2"]
    attachment_4 = REPO_ROOT / config["paths"]["attachment_4"]
    load = _wide_daily_sheet(attachment_2, "小区负载", "load_kw")
    pv = _wide_daily_sheet(attachment_2, "光伏发电实际功率", "pv_actual_kw")
    variable_price = _wide_daily_sheet(attachment_4, "Sheet1", "variable_price_yuan_per_kwh")

    panel = load.merge(pv, on=["date", "interval_end"], validate="one_to_one")
    panel = panel.merge(variable_price, on=["date", "interval_end"], validate="one_to_one")
    panel["step_of_day"] = panel.groupby("date").cumcount() + 1
    fixed_price = q1.set_index("step")["price_yuan_per_kwh"]
    panel["fixed_price_yuan_per_kwh"] = panel["step_of_day"].map(fixed_price)
    panel["interval_start"] = panel["interval_end"] - pd.Timedelta(minutes=config["time_step_minutes"])
    panel["duration_h"] = config["time_step_minutes"] / 60
    panel["net_load_kw"] = panel["load_kw"] - panel["pv_actual_kw"]

    columns = [
        "date",
        "step_of_day",
        "interval_start",
        "interval_end",
        "duration_h",
        "load_kw",
        "pv_actual_kw",
        "net_load_kw",
        "fixed_price_yuan_per_kwh",
        "variable_price_yuan_per_kwh",
    ]
    panel = panel[columns].sort_values("interval_end").reset_index(drop=True)
    if len(panel) != 365 * 144:
        raise ValueError(f"Expected 52560 actual intervals, found {len(panel)}")
    if panel.isna().any().any():
        raise ValueError("Actual panel contains missing values")
    if (panel[["load_kw", "pv_actual_kw"]] < 0).any().any():
        raise ValueError("Actual load or PV contains negative values")
    return panel


def _parse_issue_date(value: Any, current: str | None) -> str:
    if pd.isna(value) or str(value).strip() == "":
        if current is None:
            raise ValueError("Forecast table starts with a missing date")
        return current
    return str(value).strip()


def _build_forecast_panel(config: dict[str, Any]) -> pd.DataFrame:
    source = REPO_ROOT / config["paths"]["attachment_3"]
    raw = pd.read_excel(source)
    date_column, issue_column = raw.columns[:2]
    forecast_columns = list(raw.columns[2:])
    current_date: str | None = None
    records: list[dict[str, Any]] = []

    for _, row in raw.iterrows():
        current_date = _parse_issue_date(row[date_column], current_date)
        issue_date = pd.to_datetime(current_date)
        issue_hour = int(str(row[issue_column]).split(":")[0])
        issue_datetime = issue_date + pd.Timedelta(hours=issue_hour)
        for lead_hour, column in enumerate(forecast_columns, start=1):
            records.append(
                {
                    "issue_date": issue_date,
                    "issue_hour": issue_hour,
                    "issue_datetime": issue_datetime,
                    "lead_hour": lead_hour,
                    "target_datetime": issue_datetime + pd.Timedelta(hours=lead_hour),
                    "pv_forecast_kw": float(row[column]),
                }
            )

    panel = pd.DataFrame.from_records(records)
    panel = panel.sort_values(["issue_datetime", "lead_hour"]).reset_index(drop=True)
    expected_rows = 365 * len(config["forecast_issue_hours"]) * 24
    if len(panel) != expected_rows:
        raise ValueError(f"Expected {expected_rows} forecast rows, found {len(panel)}")
    if panel["pv_forecast_kw"].isna().any() or (panel["pv_forecast_kw"] < 0).any():
        raise ValueError("Forecast panel contains missing or negative PV values")
    return panel


def main() -> None:
    config = _load_config()
    q1 = _build_q1(config)
    actual = _build_actual_panel(config, q1)
    forecast = _build_forecast_panel(config)

    outputs = {
        "q1": REPO_ROOT / config["paths"]["q1_processed"],
        "actual": REPO_ROOT / config["paths"]["actual_processed"],
        "forecast": REPO_ROOT / config["paths"]["forecast_processed"],
    }
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    q1.to_csv(outputs["q1"], index=False, float_format="%.8f")
    actual.to_csv(outputs["actual"], index=False, float_format="%.8f", date_format="%Y-%m-%d %H:%M:%S")
    forecast.to_csv(outputs["forecast"], index=False, float_format="%.8f", date_format="%Y-%m-%d %H:%M:%S")

    report = {
        "status": "pass",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "random_seed": config["random_seed"],
        "time_step_minutes": config["time_step_minutes"],
        "outputs": {
            "q1": {"path": str(outputs["q1"].relative_to(REPO_ROOT)), "rows": len(q1)},
            "actual": {
                "path": str(outputs["actual"].relative_to(REPO_ROOT)),
                "rows": len(actual),
                "date_min": actual["date"].min().date().isoformat(),
                "date_max": actual["date"].max().date().isoformat(),
            },
            "forecast": {
                "path": str(outputs["forecast"].relative_to(REPO_ROOT)),
                "rows": len(forecast),
                "issue_min": forecast["issue_datetime"].min().isoformat(),
                "issue_max": forecast["issue_datetime"].max().isoformat(),
            },
        },
    }
    report_path = REPO_ROOT / config["paths"]["preparation_report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Q1 rows: {len(q1)}")
    print(f"Actual rows: {len(actual)}")
    print(f"Forecast rows: {len(forecast)}")
    print(report_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
