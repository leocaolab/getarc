#!/usr/bin/env python3
"""Fetch the arc binary for this machine from getarc's public releases.

  fetch_arc.py --stage-dir DIR                 download + unpack into DIR, then
                                               report its version and which of the
                                               route's verbs it has. Installs nothing.
  fetch_arc.py --stage-dir DIR --install-to D  also move it to D/arc — only after the
                                               person chose D (a directory on PATH).
  fetch_arc.py --tag <tag> …                   a named release instead of the latest —
                                               the only way to a prerelease (a design
                                               partner's preview tag): GitHub's "latest"
                                               skips prereleases.

Output: one JSON object (release tag, asset, staged path, version, missing verbs,
installed path). A failure is reported with the raw error, never retried quietly.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

ROADMAP = Path(__file__).resolve().parent.parent / "roadmap.json"
REPO = "leocaolab/getarc"


def latest_tag() -> str:
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["tag_name"]


def unpack(archive: Path, into: Path) -> Path:
    """Extract only a top-level regular file named `arc`; refuse anything else."""
    with tarfile.open(archive) as t:
        member = next((m for m in t.getmembers() if m.name.lstrip("./") == "arc" and m.isfile()), None)
        if member is None:
            raise RuntimeError(f"{archive.name} holds no top-level `arc` file: {[m.name for m in t.getmembers()]}")
        src = t.extractfile(member)
        assert src is not None  # a regular file always yields a reader
        dest = into / "arc"
        dest.write_bytes(src.read())
        dest.chmod(0o755)
        return dest


def verbs_missing(binary: Path, verbs: list[str]) -> dict[str, str]:
    missing = {}
    for v in verbs:
        p = subprocess.run([str(binary), v, "--help"], capture_output=True, text=True)
        if p.returncode != 0:
            missing[v] = p.stderr.strip().splitlines()[0] if p.stderr.strip() else f"exit {p.returncode}"
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage-dir", required=True, help="an empty scratch directory to download into")
    ap.add_argument("--install-to", help="directory to move arc into (the person's choice)")
    ap.add_argument("--tag", help="release tag (default: the latest)")
    a = ap.parse_args()

    roadmap = json.loads(ROADMAP.read_text())
    out: dict[str, Any] = {"platform": f"{platform.system()} {platform.machine()}"}
    asset = roadmap["assets"].get(out["platform"])
    if asset is None:
        out["error"] = f"getarc ships no binary for {out['platform']}; assets: {roadmap['assets']}"
        print(json.dumps(out, indent=2))
        return 1
    try:
        tag = a.tag or latest_tag()
        url = f"https://github.com/{REPO}/releases/download/{tag}/{asset}"
        stage = Path(a.stage_dir)
        stage.mkdir(parents=True, exist_ok=True)
        archive = stage / asset
        urllib.request.urlretrieve(url, archive)
        binary = unpack(archive, stage)
        version = subprocess.run([str(binary), "--version"], capture_output=True, text=True)
        out.update({"tag": tag, "url": url, "staged": str(binary),
                    "version": (version.stdout or version.stderr).strip(),
                    "missing_verbs": verbs_missing(binary, roadmap["required_verbs"])})
        if a.install_to:
            dest = Path(a.install_to).expanduser() / "arc"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(binary), dest)
            out["installed"] = str(dest)
            out["on_path"] = shutil.which("arc") == str(dest)
    except Exception as e:  # report every failure verbatim — the agent decides what next
        out["error"] = f"{type(e).__name__}: {e}"
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
