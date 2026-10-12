#!/usr/bin/env python3
"""Troubleshoot one failed step: its raw output, matched against known_issues.json.

Two ways in:
  diagnose.py -- <command> [args…]   run the command (the caller vouches it is one it
                                      may run — this script adds no permission) and
                                      diagnose what it printed;
  diagnose.py --from <file|->        diagnose output already captured (for a command
                                      that must not be run twice).

Output: one JSON object — the command, its exit code, the raw stdout/stderr tails
(the truth, always included), every known issue whose pattern matched with the
captured groups, and the facts that usually explain a failure (arc version and
path, tars home, platform). No match → "matches": [] and the raw output stands
on its own: the caller reports it verbatim rather than guessing.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ISSUES = Path(__file__).resolve().parent.parent / "known_issues.json"


def tail(text: str, n: int = 4000) -> str:
    return text if len(text) <= n else "…" + text[-n:]


def run(argv: list[str]) -> dict[str, Any]:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=900)
        return {"command": argv, "exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except FileNotFoundError as e:
        return {"command": argv, "exit": None, "stdout": "", "stderr": f"No such file or directory: '{argv[0]}' ({e})"}
    except subprocess.TimeoutExpired as e:
        return {"command": argv, "exit": None, "stdout": e.stdout or "", "stderr": f"timed out after 900s ({e})"}


def matches(text: str, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for issue in issues:
        m = re.search(issue["pattern"], text)
        if m:
            out.append({"id": issue["id"], "stage": issue["stage"], "matched": m.group(0),
                        "groups": list(m.groups()), "cause": issue["cause"], "fix": issue["fix"],
                        "source": issue["source"]})
    return out


def facts(arc: str) -> dict[str, Any]:
    path = shutil.which(arc)
    version = None
    if path:
        p = subprocess.run([path, "--version"], capture_output=True, text=True)
        version = (p.stdout or p.stderr).strip()
    return {"arc_path": path, "arc_version": version, "TARS_HOME": os.environ.get("TARS_HOME"),
            "platform": f"{platform.system()} {platform.machine()}", "cwd": os.getcwd()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="source", help="a file of captured output, or - for stdin")
    ap.add_argument("--arc", default="arc")
    ap.add_argument("command", nargs=argparse.REMAINDER, help="-- <command> [args…]")
    a = ap.parse_args()

    cmd = [c for c in a.command if c != "--"] if a.command else []
    if a.source:
        text = sys.stdin.read() if a.source == "-" else Path(a.source).read_text(errors="replace")
        ran = {"command": None, "exit": None, "stdout": text, "stderr": ""}
    elif cmd:
        ran = run(cmd)
    else:
        ap.error("give -- <command> or --from <file|->")

    issues = json.loads(ISSUES.read_text())["issues"]
    combined = f"{ran['stdout']}\n{ran['stderr']}"
    print(json.dumps({**ran, "stdout": tail(ran["stdout"]), "stderr": tail(ran["stderr"]),
                      "matches": matches(combined, issues), "facts": facts(a.arc)},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
