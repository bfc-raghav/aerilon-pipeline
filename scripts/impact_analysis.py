#!/usr/bin/env python3
"""Semantic 'what really changed?' analysis.

The brief: 'a patch that looks small in code can have an unclear operational
impact'. So don't just diff lines — classify the change:
  - touched flight parameter files?     (app/config/params.yaml)
  - touched interface definitions?      (app/interfaces/*)
  - touched safety-tagged modules?      (any file containing # SAFETY-CRITICAL)
This is deliberately simple; the point is the *category* of evidence, and it
extends naturally (MAVLink dialect diffs, PX4 param diffs) if time allows.
"""
import argparse
import json
import subprocess


def sh(cmd: str) -> list[str]:
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def previous_ref() -> str:
    tags = sh("git tag --sort=-creatordate")
    return tags[0] if tags else "HEAD~1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = previous_ref()
    try:
        files = sh(f"git diff --name-only {base}..HEAD")
    except Exception:
        files = []

    params_changed = any(f.startswith("app/config/") for f in files)
    interfaces_changed = any(f.startswith("app/interfaces/") for f in files)

    safety_touched = []
    for f in files:
        marked = sh(f"git grep -l 'SAFETY-CRITICAL' -- {f} 2>/dev/null || true")
        if marked:
            safety_touched.append(f)

    impact = {
        "baseline": base,
        "files_changed": files,
        "flight_parameters_changed": params_changed,
        "interfaces_changed": interfaces_changed,
        "interface_change_approved": False,  # set True via commit trailer if agreed
        "safety_critical_files_touched": safety_touched,
        "classification": (
            "parameter-affecting" if params_changed
            else "interface-affecting" if interfaces_changed
            else "behavioural"
        ),
    }
    with open(args.out, "w") as f:
        json.dump(impact, f, indent=2)
    print(json.dumps(impact, indent=2))


if __name__ == "__main__":
    main()
