"""Run the validated data-entry stages of the Problem C workflow."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "validate": REPO_ROOT / "src/preprocessing/problem_c_01_validate_raw_cc_v01.py",
    "prepare": REPO_ROOT / "src/preprocessing/problem_c_02_build_panel_cc_v01.py",
}


def run_stage(name: str) -> None:
    print(f"\n[problem_c] running stage: {name}")
    subprocess.run([sys.executable, str(STAGES[name])], cwd=REPO_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Problem C reproducible workflow")
    parser.add_argument(
        "--stage",
        choices=["validate", "prepare", "all"],
        default="all",
        help="Pipeline stage to run",
    )
    args = parser.parse_args()

    selected = list(STAGES) if args.stage == "all" else [args.stage]
    for stage in selected:
        run_stage(stage)
    print("\n[problem_c] completed")


if __name__ == "__main__":
    main()
