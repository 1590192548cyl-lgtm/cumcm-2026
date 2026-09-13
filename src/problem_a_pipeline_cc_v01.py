"""Orchestrate Problem A input checks, solvers, exports, and result gates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config/problem_a_config_v01.json"


def _load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _run(command: list[str], env: dict[str, str] | None = None) -> None:
    print(f"\n[problem_a] running: {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def _resolve_node() -> Path:
    configured = os.environ.get("CUMCM_NODE")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    system_node = shutil.which("node")
    if system_node:
        candidates.append(Path(system_node))
    runtime_root = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    )
    candidates.extend([runtime_root / "bin/node", runtime_root / "node.exe"])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(
        "Node.js was not found. Set CUMCM_NODE to the Node executable before export."
    )


def _node_environment() -> dict[str, str]:
    environment = os.environ.copy()
    if "CUMCM_NODE_MODULES" not in environment:
        candidate = (
            Path.home()
            / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
        )
        if candidate.exists():
            environment["CUMCM_NODE_MODULES"] = str(candidate)
    return environment


def _quick_gate(output_root: Path) -> None:
    required = [
        output_root / "results/problem_a_result_03_preheat_diagnostics_v01.json",
        output_root / "results/problem_a_result_09_full_drying_diagnostics_v01.json",
        output_root / "figures/problem_a_figure_01_preheat_profiles_v01.png",
        output_root / "figures/problem_a_figure_02_q2_profiles_v01.png",
        output_root / "figures/problem_a_figure_03_drying_comparison_v01.png",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Quick profile is missing outputs: {missing}")
    diagnostics = json.loads(required[1].read_text(encoding="utf-8"))
    if not diagnostics["physical_checks"]["q3_moisture_nonnegative"]:
        raise RuntimeError("Quick profile produced negative moisture in Question 3")
    if not diagnostics["physical_checks"]["q4_moisture_nonnegative"]:
        raise RuntimeError("Quick profile produced negative moisture in Question 4")
    print("\n[problem_a] quick gate: PASS", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=["inputs", "q1", "q234", "export", "check", "all"],
        default="inputs",
    )
    parser.add_argument(
        "--profile",
        choices=["quick", "final"],
        default="quick",
        help="Quick writes isolated smoke outputs; final writes official outputs.",
    )
    parser.add_argument(
        "--submission-gate",
        action="store_true",
        help="Fail the final check when a documented warning remains.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_config()
    profile = config["profiles"][args.profile]
    output_root = REPO_ROOT / config["paths"][
        "quick_output_root" if args.profile == "quick" else "official_output_root"
    ]
    python = sys.executable

    commands = {
        "inputs": [
            python,
            "src/preprocessing/problem_a_00_validate_inputs_cc_v01.py",
        ],
        "q1": [
            python,
            "src/models/problem_a_01_preheat_pde_cc_v01.py",
            "--input",
            config["paths"]["air_conditions"],
            "--output-root",
            str(output_root.relative_to(REPO_ROOT)),
            "--final-intervals",
            str(profile["q1_intervals"]),
        ],
        "q234": [
            python,
            "src/models/problem_a_03_full_drying_pde_cc_v01.py",
            "--air-input",
            config["paths"]["air_conditions"],
            "--radius-input",
            config["paths"]["radius_history"],
            "--output-root",
            str(output_root.relative_to(REPO_ROOT)),
            "--q2-intervals",
            str(profile["q2_intervals"]),
            "--drying-intervals",
            str(profile["drying_intervals"]),
        ],
        "check": [
            python,
            "src/analysis/problem_a_06_validate_outputs_cc_v01.py",
        ],
    }
    if args.submission_gate:
        commands["check"].append("--submission-gate")

    if args.stage == "inputs":
        _run(commands["inputs"])
    elif args.stage in ("q1", "q234"):
        _run(commands["inputs"])
        _run(commands[args.stage])
    elif args.stage == "export":
        if args.profile != "final":
            raise ValueError("Export is only available with --profile final")
        node = _resolve_node()
        _run(
            [
                str(node),
                "src/visualization/problem_a_04_export_official_results_cc_v01.mjs",
                "all",
            ],
            env=_node_environment(),
        )
    elif args.stage == "check":
        if args.profile != "final":
            raise ValueError("Official output checks require --profile final")
        _run(commands["check"])
    else:
        _run(commands["inputs"])
        _run(commands["q1"])
        _run(commands["q234"])
        if args.profile == "quick":
            _quick_gate(output_root)
        else:
            node = _resolve_node()
            _run(
                [
                    str(node),
                    "src/visualization/problem_a_04_export_official_results_cc_v01.mjs",
                    "all",
                ],
                env=_node_environment(),
            )
            _run(commands["check"])

    print("\n[problem_a] workflow completed", flush=True)


if __name__ == "__main__":
    main()
