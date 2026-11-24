#!/usr/bin/env python3
"""Run the bounded Base64 tail probe on pinned JDK builds in Docker."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = (
    ("jdk17_0_6", "17.0.6", 62),
    ("jdk17_0_5", "17.0.5", 0),
    ("jdk17_0_6_no_intrinsics", "17.0.6", 0),
)


def docker(*arguments: str) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose", "-f", "compose.yaml", *arguments]
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, text=True, encoding="utf-8",
                          errors="replace", stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def main() -> int:
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] != "--skip-build"):
        print("usage: python verify.py [--skip-build]", file=sys.stderr)
        return 1

    if len(sys.argv) == 1:
        try:
            build = docker("build", "jdk17_0_6", "jdk17_0_5")
        except FileNotFoundError:
            print("Docker CLI was not found.", file=sys.stderr)
            return 1
        if build.returncode:
            print(build.stdout[-4000:] + build.stderr[-4000:], file=sys.stderr)
            return 1

    failures: list[str] = []
    results: dict[str, int] = {}
    for service, expected_java, expected_changed in CASES:
        try:
            result = docker("run", "--rm", "-T", service)
        except FileNotFoundError:
            print("Docker CLI was not found.", file=sys.stderr)
            return 1
        if result.returncode:
            print(result.stdout + result.stderr, file=sys.stderr)
            return 1
        try:
            record = next(json.loads(line) for line in result.stdout.splitlines()
                          if line.startswith('{"probe":'))
        except (StopIteration, json.JSONDecodeError):
            print("No probe JSON found in Docker output:\n" + result.stdout
                  + result.stderr, file=sys.stderr)
            return 1

        changed = record.get("changedAfterLogicalEnd")
        results[service] = changed
        print(f"{service}: Java {record.get('java')}, changed offsets 98..159 = "
              f"{changed}, exception = {record.get('exception')}", flush=True)
        if not str(record.get("java", "")).startswith(expected_java):
            failures.append(f"{service}: unexpected Java version")
        if (record.get("inputLength"), record.get("logicalOutputLength"),
                record.get("destinationLength")) != (129, 98, 160):
            failures.append(f"{service}: unexpected probe dimensions")
        if record.get("exception") != "IllegalArgumentException":
            failures.append(f"{service}: expected malformed-input exception")
        if service != "jdk17_0_6" and changed != expected_changed:
            failures.append(f"{service}: expected {expected_changed} changed bytes")

    if failures:
        print("FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    if results["jdk17_0_6"] == 0:
        print("INCONCLUSIVE: the affected JDK did not use the measured AVX-512 path "
              "on this host. Check the CPU features available inside Docker.")
        return 2
    if results["jdk17_0_6"] != 62:
        print("FAIL: expected 62 changed bytes on the affected JDK.", file=sys.stderr)
        return 1
    print("PASS: 62 changed bytes on 17.0.6+10; both controls changed 0 bytes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
