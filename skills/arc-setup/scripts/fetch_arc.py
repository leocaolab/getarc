#!/usr/bin/env python3
"""Fetch the arc binary for this machine from a release.

  fetch_arc.py --stage-dir DIR                 download + unpack into DIR, then
                                               report its version and which of the
                                               route's verbs it has. Installs nothing.
  fetch_arc.py --stage-dir DIR --install-to D  also move it to D/arc — only after the
                                               person chose D (a directory on PATH).
  fetch_arc.py --version vX.Y.Z …              fetch that getarc release — the way to a
                                               prerelease (a design partner's preview tag),
                                               which GitHub's "latest" skips.
  fetch_arc.py --from URL …                    fetch URL/<asset> (a mirror, or a file://
                                               directory).

--version and --from are mutually exclusive.

Output: one JSON object — platform, url (where it fetched from), staged, version,
missing_verbs, and after --install-to also installed and on_path; on failure, error with
the raw error, never retried quietly.
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
RELEASES = "https://github.com/leocaolab/getarc/releases"


def release_base(version: str | None, mirror: str | None) -> str:
    if mirror:
        return mirror.rstrip("/")
    if version:
        return f"{RELEASES}/download/{version}"
    return f"{RELEASES}/latest/download"


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
    release = ap.add_mutually_exclusive_group()
    release.add_argument("--version", help="getarc release tag, e.g. vX.Y.Z (default: the latest)")
    release.add_argument("--from", dest="mirror", metavar="URL",
                         help="fetch URL/<asset> (a mirror, or a file:// directory)")
    a = ap.parse_args()

    roadmap = json.loads(ROADMAP.read_text())
    out: dict[str, Any] = {"platform": f"{platform.system()} {platform.machine()}"}
    asset = roadmap["assets"].get(out["platform"])
    if asset is None:
        out["error"] = f"no arc build for {out['platform']}; assets: {roadmap['assets']}"
        print(json.dumps(out, indent=2))
        return 1
    try:
        url = f"{release_base(a.version, a.mirror)}/{asset}"
        stage = Path(a.stage_dir)
        stage.mkdir(parents=True, exist_ok=True)
        archive = stage / asset
        urllib.request.urlretrieve(url, archive)
        binary = unpack(archive, stage)
        version = subprocess.run([str(binary), "--version"], capture_output=True, text=True)
        out.update({"url": url, "staged": str(binary),
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
