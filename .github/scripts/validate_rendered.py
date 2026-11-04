#!/usr/bin/env python3
"""Validate rendered manifests and reject new Checkov findings vs. the PR base."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def _run(command: list[str], *, timeout: int = 180) -> tuple[int | None, str, str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, "", f"{type(exc).__name__}: {exc}"
    return result.returncode, result.stdout, result.stderr


def _checkov_findings(path: Path) -> tuple[Counter[tuple[str, str]] | None, str]:
    code, stdout, stderr = _run(
        [
            "checkov",
            "--framework",
            "kubernetes",
            "--skip-download",
            "--file",
            str(path),
            "--output",
            "json",
        ]
    )
    if code not in {0, 1}:
        return None, f"Checkov exited with {code}: {stderr[-2000:]}"
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return None, f"Checkov did not return valid JSON: {exc}; {stderr[-1000:]}"

    reports = payload if isinstance(payload, list) else [payload]
    findings: Counter[tuple[str, str]] = Counter()
    for report in reports:
        results = report.get("results") if isinstance(report, dict) else None
        failures = results.get("failed_checks") if isinstance(results, dict) else None
        if not isinstance(failures, list):
            return None, "Checkov JSON is missing results.failed_checks"
        for finding in failures:
            if not isinstance(finding, dict):
                return None, "Checkov returned an invalid failed-check record"
            check_id = finding.get("check_id")
            resource = finding.get("resource")
            if not isinstance(check_id, str) or not isinstance(resource, str):
                return None, "Checkov finding has no stable check_id/resource identity"
            findings[(check_id, resource)] += 1
    return findings, ""


def _finding_rows(findings: Counter[tuple[str, str]]) -> list[dict[str, Any]]:
    return [
        {"check_id": check_id, "resource": resource, "count": count}
        for (check_id, resource), count in sorted(findings.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    started = time.monotonic()
    report: dict[str, Any] = {
        "status": "FAIL",
        "checks": {"kubeconform": "ERROR", "conftest": "ERROR", "checkov": "ERROR"},
        "reasons": {},
        "checkov_baseline_count": None,
        "checkov_candidate_count": None,
        "new_findings": [],
    }

    for label, command in (
        (
            "kubeconform",
            ["kubeconform", "-strict", "-summary", str(args.candidate)],
        ),
        (
            "conftest",
            ["conftest", "test", "--policy", str(args.policy), str(args.candidate)],
        ),
    ):
        code, stdout, stderr = _run(command)
        report["checks"][label] = "PASS" if code == 0 else "FAIL"
        report["reasons"][label] = {
            "exit_code": code,
            "stdout": stdout[-4000:],
            "stderr": stderr[-2000:],
        }

    baseline, baseline_error = _checkov_findings(args.baseline)
    candidate, candidate_error = _checkov_findings(args.candidate)
    if baseline is None or candidate is None:
        report["checks"]["checkov"] = "ERROR"
        report["reasons"]["checkov"] = baseline_error or candidate_error
    else:
        new_findings = candidate - baseline
        report["checkov_baseline_count"] = sum(baseline.values())
        report["checkov_candidate_count"] = sum(candidate.values())
        report["new_findings"] = _finding_rows(new_findings)
        report["checks"]["checkov"] = "PASS" if not new_findings else "FAIL"
        report["reasons"]["checkov"] = {
            "baseline_findings": report["checkov_baseline_count"],
            "candidate_findings": report["checkov_candidate_count"],
            "new_findings": report["new_findings"],
        }

    report["duration_ms"] = round((time.monotonic() - started) * 1000)
    passed = all(value == "PASS" for value in report["checks"].values())
    report["status"] = "PASS" if passed else "FAIL"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for name, status in report["checks"].items():
        print(f"{name}: {status}")
    if baseline is not None and candidate is not None:
        print(
            "Checkov findings: "
            f"baseline={report['checkov_baseline_count']}, "
            f"candidate={report['checkov_candidate_count']}, "
            f"new={len(report['new_findings'])}"
        )
        for finding in report["new_findings"]:
            print(f"NEW {finding['check_id']} {finding['resource']}")
    print(f"Validation result: {report['status']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
