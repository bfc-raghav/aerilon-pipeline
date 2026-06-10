#!/usr/bin/env python3
"""Generate the signed Release Evidence Pack.

The evidence pack is the product. It answers, machine-readably and
human-readably, the four questions in the brief:
  1. What has changed?          -> change + impact sections
  2. What was tested?           -> tests / coverage / sitl / static_analysis
  3. What remains uncertain?    -> uncertainties (explicit, first-class)
  4. Is it ready to accept?     -> each org's policy decides from this file
"""
import argparse
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def parse_junit(path: str) -> dict:
    if not os.path.exists(path):
        return {"executed": False, "total": 0, "failed": 0, "errors": 0, "skipped": 0}
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return {
        "executed": True,
        "total": int(suite.get("tests", 0)),
        "failed": int(suite.get("failures", 0)),
        "errors": int(suite.get("errors", 0)),
        "skipped": int(suite.get("skipped", 0)),
    }


def parse_coverage(path: str) -> dict:
    if not os.path.exists(path):
        return {"percent": 0.0}
    with open(path) as f:
        data = json.load(f)
    return {"percent": round(data.get("totals", {}).get("percent_covered", 0.0), 1)}


def parse_ruff(path: str) -> dict:
    if not os.path.exists(path):
        return {"error_count": 0, "executed": False}
    with open(path) as f:
        try:
            findings = json.load(f)
        except json.JSONDecodeError:
            findings = []
    return {"executed": True, "error_count": len(findings)}


def load_json(path: str, default: dict) -> dict:
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def collect_uncertainties(tests, sitl, impact) -> list:
    """Honest, automatic declaration of what this evidence does NOT cover."""
    u = []
    if not sitl.get("executed"):
        u.append("No SITL simulation evidence for this build; "
                 "behavioural change under flight conditions is unverified.")
    u.append("No hardware-in-the-loop or live flight test performed in pipeline; "
             "companion-computer software only.")
    if impact.get("flight_parameters_changed"):
        u.append("Flight parameters changed; tuning impact on this airframe unmeasured.")
    if tests.get("skipped", 0) > 0:
        u.append(f"{tests['skipped']} unit tests skipped.")
    return u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--junit"), ap.add_argument("--coverage")
    ap.add_argument("--impact"), ap.add_argument("--sitl"), ap.add_argument("--ruff")
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    tests = parse_junit(args.junit)
    coverage = parse_coverage(args.coverage)
    static = parse_ruff(args.ruff)
    impact = load_json(args.impact, {"flight_parameters_changed": False,
                                     "interfaces_changed": False, "files_changed": []})
    sitl = load_json(args.sitl, {"executed": False})

    commit_msg = sh("git log -1 --pretty=%s")
    pack = {
        "schema": "aerilon-evidence/v1",
        "version": args.version,
        "generated": datetime.now(timezone.utc).isoformat(),
        "change": {
            "commit": sh("git rev-parse HEAD"),
            "author": sh("git log -1 --pretty=%an"),
            "message": commit_msg,
            "linked_issue": ("#" in commit_msg) or None,  # e.g. "fix camera lag (#42)"
            "files_changed": impact.get("files_changed", []),
        },
        "impact": impact,
        "tests": tests,
        "coverage": coverage,
        "static_analysis": static,
        "sitl": sitl,
        "uncertainties": collect_uncertainties(tests, sitl, impact),
    }

    with open(args.out, "w") as f:
        json.dump(pack, f, indent=2)

    # Human-readable one-pager for the approver's phone screen.
    lines = [
        f"# Release Evidence — v{args.version}",
        f"**Change:** {pack['change']['message']} ({pack['change']['commit'][:8]} by {pack['change']['author']})",
        f"**Tests:** {tests['total'] - tests['failed'] - tests['errors']}/{tests['total']} passed, "
        f"{tests['skipped']} skipped | **Coverage:** {coverage['percent']}%",
        f"**Static analysis:** {static['error_count']} findings",
        f"**Operational impact:** flight params changed = {impact.get('flight_parameters_changed')}, "
        f"interfaces changed = {impact.get('interfaces_changed')}",
        "", "## What remains uncertain",
        *[f"- {u}" for u in pack["uncertainties"]],
    ]
    with open(args.summary, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Evidence pack written: {args.out}")


if __name__ == "__main__":
    main()
