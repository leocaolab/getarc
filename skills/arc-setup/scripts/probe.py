#!/usr/bin/env python3
"""Report where an arc install stands against roadmap.json — read-only.

Every criterion is judged from the world as it is now (files, PATH, git), so an
install that stopped half-way resumes by running this again. It changes nothing the
person wrote: the one arc command it runs in their repo, `arc rot --no-judge`, lets arc
create its own `.arc/.gitignore` and `.arc/tars/` (as every arc run does); `arc init`
runs only in a throwaway repo. It never prints a credential's value: for an env-var
credential it says only whether the variable is set.

Output: one JSON object on stdout —
  {"stages": [{"id", "title", "optional", "done", "criteria": [{"id", "level",
   "ok", "says", "facts"}]}], "next": <first non-optional stage not done | null>}
"ok" is true / false, or null when the check could not decide; "facts" carries
what was seen (raw output, paths), so a failure arrives with its evidence.
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
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # older python3: the TOML checks report "cannot decide"
    tomllib = None  # type: ignore[assignment]

ROADMAP = Path(__file__).resolve().parent.parent / "roadmap.json"

# tars provider `type` → model family. Types that can front any model
# (openai_compat, vllm, bedrock, …) have no family of their own: None, and the
# agent asks the person instead of guessing.
FAMILY = {
    "anthropic": "anthropic", "claude_cli": "anthropic", "claude_sdk": "anthropic",
    "openai": "openai", "codex_cli": "openai",
    "gemini": "google", "antigravity": "google",
}
# Provider types that run as a local agent CLI, and their default executable
# (tars-config providers.rs `default_*_executable`).
CLI_EXECUTABLE = {
    "claude_cli": "claude", "codex_cli": "codex", "antigravity": "agy",
    "opencode": "opencode", "claude_sdk": "node",
}
KNOWN_TYPES = {
    "openai", "openai_compat", "anthropic", "gemini", "bedrock", "vllm", "mlx",
    "llamacpp", "claude_cli", "claude_sdk", "codex_cli", "opencode", "antigravity",
}
CRITIC_ROLES = ("critic_l4", "critic", "default")


@dataclass
class Ctx:
    repo: Path
    home: Path
    tars_home: Path
    arc: str
    roadmap: dict[str, Any]
    cache: dict[str, Any] = field(default_factory=dict)


@dataclass
class Verdict:
    ok: bool | None
    facts: dict[str, Any]


def run(argv: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int | None, str, str]:
    """Run a read-only command; (exit, stdout, stderr). exit None = could not start."""
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError as e:
        return None, "", str(e)
    except subprocess.TimeoutExpired:
        return None, "", f"timed out after {timeout}s: {' '.join(argv)}"


def tail(text: str, n: int = 1200) -> str:
    return text if len(text) <= n else "…" + text[-n:]


def read_toml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """(table, None) or (None, why it could not be read)."""
    if tomllib is None:
        return None, f"python {platform.python_version()} has no tomllib (needs 3.11+)"
    if not path.is_file():
        return None, f"{path} does not exist"
    try:
        return tomllib.loads(path.read_text()), None
    except (tomllib.TOMLDecodeError, OSError) as e:
        return None, f"{path}: {e}"


# ── shared reads (memoised on ctx) ────────────────────────────────────────

def tars(ctx: Ctx) -> tuple[dict[str, Any] | None, str | None]:
    if "tars" not in ctx.cache:
        ctx.cache["tars"] = read_toml(ctx.tars_home / "config.toml")
    return ctx.cache["tars"]


def providers(ctx: Ctx) -> dict[str, dict[str, Any]]:
    table, _ = tars(ctx)
    p = (table or {}).get("providers", {})
    return p if isinstance(p, dict) else {}


def arc_config(ctx: Ctx) -> tuple[dict[str, Any] | None, str | None]:
    if "arc_config" not in ctx.cache:
        ctx.cache["arc_config"] = read_toml(ctx.repo / ".arc" / "config.toml")
    return ctx.cache["arc_config"]


def roles(ctx: Ctx) -> dict[str, str]:
    cfg, _ = arc_config(ctx)
    r = (cfg or {}).get("roles", {})
    return {k: v for k, v in r.items() if isinstance(v, str)} if isinstance(r, dict) else {}


def critic_id(ctx: Ctx) -> str | None:
    r = roles(ctx)
    return next((r[k] for k in CRITIC_ROLES if k in r), None)


def origin_name(ctx: Ctx) -> str | None:
    code, out, _ = run(["git", "remote", "get-url", "origin"], cwd=ctx.repo)
    if code != 0:
        return None
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", out.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


# ── checks: one per criterion id in roadmap.json ──────────────────────────

def git_repo(ctx: Ctx) -> Verdict:
    code, out, err = run(["git", "rev-parse", "--show-toplevel"], cwd=ctx.repo)
    return Verdict(code == 0, {"toplevel": out.strip()} if code == 0 else {"raw": err.strip()})


def platform_ok(ctx: Ctx) -> Verdict:
    key = f"{platform.system()} {platform.machine()}"
    asset = ctx.roadmap["assets"].get(key)
    return Verdict(asset is not None, {"platform": key, "asset": asset})


def python_toml(_: Ctx) -> Verdict:
    return Verdict(tomllib is not None, {"python": platform.python_version()})


def arc_on_path(ctx: Ctx) -> Verdict:
    path = shutil.which(ctx.arc)
    if path is None:
        return Verdict(False, {"raw": f"`{ctx.arc}` is not on PATH", "PATH": os.environ.get("PATH", "")})
    code, out, err = run([path, "--version"])
    return Verdict(code == 0, {"path": path, "version": out.strip() or err.strip()})


def arc_has_verbs(ctx: Ctx) -> Verdict:
    path = shutil.which(ctx.arc)
    if path is None:
        return Verdict(False, {"raw": "arc is not on PATH"})
    missing = {}
    for verb in ctx.roadmap["required_verbs"]:
        code, _, err = run([path, verb, "--help"])
        if code != 0:
            missing[verb] = tail(err.strip(), 300)
    return Verdict(not missing, {"missing": missing} if missing else {"verbs": ctx.roadmap["required_verbs"]})


def tars_config_present(ctx: Ctx) -> Verdict:
    p = ctx.tars_home / "config.toml"
    return Verdict(p.is_file(), {"path": str(p)})


def tars_config_parses(ctx: Ctx) -> Verdict:
    table, why = tars(ctx)
    if table is None:
        return Verdict(None if tomllib is None else False, {"raw": why})
    ps = providers(ctx)
    listed = {pid: {"type": p.get("type"), "default_model": p.get("default_model"),
                    "family": FAMILY.get(str(p.get("type")))} for pid, p in ps.items() if isinstance(p, dict)}
    unknown = [pid for pid, p in listed.items() if p["type"] not in KNOWN_TYPES]
    return Verdict(bool(listed) and not unknown, {"providers": listed, "unknown_type": unknown})


def tars_loads_in_arc(ctx: Ctx) -> Verdict:
    """Let arc itself read the tars config: `arc init` in a throwaway git repo.

    arc lists the tars providers before it notices there is no terminal, so a malformed
    file fails here with tars's own words, and a readable one leaves an example naming
    the ids arc found. The throwaway repo is deleted; the person's repo is not touched.
    """
    with tempfile.TemporaryDirectory(prefix="arc-install-probe-") as tmp:
        if run(["git", "init", "-q", tmp])[0] != 0:
            return Verdict(None, {"raw": "git init of a scratch repo failed"})
        argv = [ctx.arc, "--tars_home", str(ctx.tars_home), "--repo", tmp, "init"]
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return Verdict(None, {"raw": str(e)})
        said = (p.stdout + p.stderr).strip()
        example = Path(tmp) / ".arc" / "config.toml.example"
        text = example.read_text() if example.is_file() else ""
        ids = re.findall(r"^#   - (\S+)$", text, re.M)
        return Verdict(bool(ids), {"exit": p.returncode, "ids_arc_sees": ids, "arc_said": tail(said)})


def provider_auth_ready(ctx: Ctx) -> Verdict:
    ps = providers(ctx)
    if not ps:
        return Verdict(None, {"raw": "no providers to check"})
    report: dict[str, str] = {}
    ok = True
    for pid, p in ps.items():
        if not isinstance(p, dict):
            continue
        secret = (p.get("auth") or {}).get("secret") or {}
        exe = p.get("executable") or CLI_EXECUTABLE.get(str(p.get("type")))
        if secret.get("source") == "env":
            var = secret.get("var")
            is_set = bool(var and os.environ.get(var))
            report[pid] = f"env var {var} is {'set' if is_set else 'NOT set in this shell'}"
            ok = ok and is_set
        elif secret.get("source") == "file":
            path = Path(os.path.expanduser(str(secret.get("path", ""))))
            report[pid] = f"key file {path} {'exists' if path.is_file() else 'does NOT exist'}"
            ok = ok and path.is_file()
        elif exe:
            found = shutil.which(exe)
            report[pid] = f"executable {exe}: {found or 'NOT on PATH'}"
            ok = ok and found is not None
        else:
            report[pid] = "no credential named (auth kind none, or none needed)"
    return Verdict(ok, {"providers": report})


def arc_config_present(ctx: Ctx) -> Verdict:
    p = ctx.repo / ".arc" / "config.toml"
    ex = ctx.repo / ".arc" / "config.toml.example"
    return Verdict(p.is_file(), {"path": str(p), "example_present": ex.is_file()})


def no_providers_section(ctx: Ctx) -> Verdict:
    cfg, why = arc_config(ctx)
    if cfg is None:
        return Verdict(None if tomllib is None else False, {"raw": why})
    return Verdict("providers" not in cfg, {"providers": sorted((cfg.get("providers") or {}).keys())})


def roles_resolve(ctx: Ctx) -> Verdict:
    cfg, why = arc_config(ctx)
    if cfg is None:
        return Verdict(None if tomllib is None else False, {"raw": why})
    r = roles(ctx)
    known = set(providers(ctx))
    dangling = {role: pid for role, pid in r.items() if pid not in known}
    critic = critic_id(ctx)
    return Verdict(critic is not None and not dangling,
                   {"roles": r, "critic": critic, "not_in_tars": dangling, "tars_ids": sorted(known)})


def fixer_explicit(ctx: Ctx) -> Verdict:
    r = roles(ctx)
    return Verdict("fixer" in r, {"fixer": r.get("fixer")})


def fixer_family_differs(ctx: Ctx) -> Verdict:
    r, ps = roles(ctx), providers(ctx)
    critic, fixer = critic_id(ctx), r.get("fixer")
    if critic is None or fixer is None:
        return Verdict(None, {"raw": "critic or fixer not set"})
    fam = {k: FAMILY.get(str((ps.get(v) or {}).get("type"))) for k, v in (("critic", critic), ("fixer", fixer))}
    facts = {"critic": critic, "fixer": fixer, "families": fam,
             "models": {k: (ps.get(v) or {}).get("default_model") for k, v in (("critic", critic), ("fixer", fixer))}}
    if None in fam.values():
        return Verdict(None, {**facts, "raw": "a provider type with no fixed family — ask which model family it serves"})
    return Verdict(fam["critic"] != fam["fixer"], facts)


def fixer_can_edit(ctx: Ctx) -> Verdict:
    fixer = roles(ctx).get("fixer")
    p = providers(ctx).get(fixer or "", {})
    kind = p.get("type")
    if kind == "claude_cli":
        tools = p.get("tools", "disabled")
        return Verdict(tools != "disabled", {"fixer": fixer, "type": kind, "tools": tools})
    if kind == "codex_cli":
        sandbox = p.get("sandbox", "read-only")
        return Verdict(sandbox == "workspace-write", {"fixer": fixer, "type": kind, "sandbox": sandbox})
    return Verdict(None if fixer else False, {"fixer": fixer, "type": kind})


def jobs_of(path: Path) -> list[str]:
    """Top-level job ids under `jobs:` — a line scan, not a YAML parser."""
    out, inside = [], False
    for line in path.read_text().splitlines():
        if re.match(r"^jobs:\s*$", line):
            inside = True
            continue
        if inside and re.match(r"^\S", line):
            break
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line) if inside else None
        if m:
            out.append(m.group(1))
    return out


def list_jobs(ctx: Ctx, rel: str, jobs: list[str]) -> Verdict:
    results = {}
    for job in jobs:
        code, out, err = run([ctx.arc, "workflow", rel, "--job", job, "--list", "--repo", str(ctx.repo)], cwd=ctx.repo)
        results[job] = {"exit": code, "output": tail((out + err).strip())}
    ok = bool(results) and all(r["exit"] == 0 for r in results.values())
    return Verdict(ok, {"file": rel, "jobs": results})


MERGE_YML = ".github/workflows/merge.yml"


def merge_yml_present(ctx: Ctx) -> Verdict:
    p = ctx.repo / MERGE_YML
    return Verdict(p.is_file(), {"path": str(p)})


def merge_yml_dispatch_only(ctx: Ctx) -> Verdict:
    p = ctx.repo / MERGE_YML
    if not p.is_file():
        return Verdict(False, {"raw": "no merge.yml"})
    text = p.read_text()
    m = re.search(r"^on:\s*\n((?:[ \t]+.*\n?)*)", text, re.M)
    triggers = re.findall(r"^[ \t]+([A-Za-z_]+):", m.group(1), re.M) if m else []
    inline = re.search(r"^on:[ \t]*(\S.*)$", text, re.M)
    return Verdict(triggers == ["workflow_dispatch"] and not inline,
                   {"triggers": triggers, "inline_on": inline.group(1) if inline else None})


def merge_yml_lists(ctx: Ctx) -> Verdict:
    p = ctx.repo / MERGE_YML
    if not p.is_file():
        return Verdict(False, {"raw": "no merge.yml"})
    return list_jobs(ctx, MERGE_YML, jobs_of(p))


def release_table(ctx: Ctx) -> dict[str, Any]:
    cfg, _ = arc_config(ctx)
    r = (cfg or {}).get("release")
    return r if isinstance(r, dict) else {}


def release_declared(ctx: Ctx) -> Verdict:
    r = release_table(ctx)
    return Verdict(bool(r.get("workflow")), {"release": r})


def release_job_lists(ctx: Ctx) -> Verdict:
    r = release_table(ctx)
    wf = r.get("workflow")
    if not wf or not (ctx.repo / wf).is_file():
        return Verdict(False, {"release": r, "raw": "no [release] workflow file"})
    job = r.get("job")
    return list_jobs(ctx, wf, [job] if isinstance(job, str) else jobs_of(ctx.repo / wf))


def release_has_concurrency(ctx: Ctx) -> Verdict:
    wf = release_table(ctx).get("workflow")
    p = ctx.repo / wf if wf else None
    if p is None or not p.is_file():
        return Verdict(False, {"raw": "no [release] workflow file"})
    return Verdict(bool(re.search(r"^\s+concurrency:", p.read_text(), re.M)), {"file": wf})


def delivery_one_build(ctx: Ctx) -> Verdict:
    r = release_table(ctx)
    table, why = read_toml(ctx.repo / ".arc" / "delivery.toml")
    if table is None:
        return Verdict(None if tomllib is None else False, {"raw": why})
    builds = table.get("builds") or {}
    same = [b for b, v in builds.items()
            if isinstance(v, dict) and v.get("workflow") == r.get("workflow") and v.get("job") == r.get("job")]
    return Verdict(len(same) == 1, {"builds_running_release": same, "release": r})


def fixer_cli_present(ctx: Ctx) -> Verdict:
    p = providers(ctx).get(roles(ctx).get("fixer") or "", {})
    exe = p.get("executable") or CLI_EXECUTABLE.get(str(p.get("type")))
    if exe is None:
        return Verdict(None, {"raw": "the fixer is not an agent CLI provider", "type": p.get("type")})
    found = shutil.which(exe)
    return Verdict(found is not None, {"executable": exe, "path": found})


def bridge_client(ctx: Ctx) -> Verdict:
    p = ctx.home / ".arc" / "client.toml"
    table, why = read_toml(p)
    if table is None:
        return Verdict(False, {"path": str(p), "raw": why})
    return Verdict(bool(table.get("web")), {"path": str(p), "web": table.get("web")})


def bridge_hooks(ctx: Ctx) -> Verdict:
    places = [ctx.repo / ".claude" / "settings.json", ctx.repo / ".claude" / "settings.local.json",
              ctx.home / ".claude" / "settings.json", ctx.repo / ".codex" / "config.toml",
              ctx.home / ".codex" / "config.toml", ctx.repo / ".agents" / "hooks.json",
              ctx.home / ".gemini" / "config" / "hooks.json"]
    found = [str(p) for p in places if p.is_file() and "arc bridge hook" in p.read_text(errors="replace")]
    return Verdict(bool(found), {"files_with_hooks": found})


def rot_offline_runs(ctx: Ctx) -> Verdict:
    code, out, err = run([ctx.arc, "rot", "--no-judge", "--repo", str(ctx.repo)], cwd=ctx.repo, timeout=300)
    return Verdict(code == 0, {"exit": code, "output": tail((out + err).strip())})


def origin_remote(ctx: Ctx) -> Verdict:
    name = origin_name(ctx)
    return Verdict(name is not None, {"origin": name})


def gh_authed(ctx: Ctx) -> Verdict:
    code, out, err = run(["gh", "auth", "status"])
    said = "\n".join(l for l in (out + err).splitlines() if "Token" not in l)
    return Verdict(code == 0, {"exit": code, "output": tail(said.strip(), 600)})


def review_service_here(ctx: Ctx) -> Verdict:
    p = ctx.home / ".arc" / "machine.toml"
    table, why = read_toml(p)
    name = origin_name(ctx)
    if table is None:
        return Verdict(False, {"path": str(p), "machine_toml_exists": p.is_file(), "raw": why, "origin": name})
    tenants = [t for t in table.get("tenant", []) if isinstance(t, dict)]
    hit = [t.get("name") for t in tenants
           if t.get("name") == name or Path(str(t.get("home", ""))).resolve() == ctx.repo.resolve()]
    return Verdict(bool(hit), {"path": str(p), "machine_toml_exists": True, "origin": name,
                               "tenants": [t.get("name") for t in tenants]})


CHECKS: dict[str, Callable[[Ctx], Verdict]] = {
    "git_repo": git_repo, "platform": platform_ok, "python_toml": python_toml,
    "arc_on_path": arc_on_path, "arc_has_verbs": arc_has_verbs,
    "tars_config_present": tars_config_present, "tars_config_parses": tars_config_parses,
    "tars_loads_in_arc": tars_loads_in_arc, "provider_auth_ready": provider_auth_ready,
    "arc_config_present": arc_config_present, "no_providers_section": no_providers_section,
    "roles_resolve": roles_resolve, "fixer_explicit": fixer_explicit,
    "fixer_family_differs": fixer_family_differs, "fixer_can_edit": fixer_can_edit,
    "merge_yml_present": merge_yml_present, "merge_yml_dispatch_only": merge_yml_dispatch_only,
    "merge_yml_lists": merge_yml_lists,
    "release_declared": release_declared, "release_job_lists": release_job_lists,
    "release_has_concurrency": release_has_concurrency, "delivery_one_build": delivery_one_build,
    "fixer_cli_present": fixer_cli_present, "bridge_client": bridge_client, "bridge_hooks": bridge_hooks,
    "rot_offline_runs": rot_offline_runs, "origin_remote": origin_remote, "gh_authed": gh_authed,
    "review_service_here": review_service_here,
}


def judge_stage(ctx: Ctx, stage: dict[str, Any]) -> dict[str, Any]:
    criteria = []
    for c in stage["criteria"]:
        v = CHECKS[c["id"]](ctx)
        criteria.append({"id": c["id"], "level": c["level"], "says": c["says"], "ok": v.ok, "facts": v.facts})
    done = all(c["ok"] is True for c in criteria if c["level"] == "required")
    return {"id": stage["id"], "title": stage["title"], "optional": stage["optional"],
            "done": done, "verify": stage["verify"], "criteria": criteria}


def default_tars_home(home: Path) -> Path:
    """arc's own order: --tars_home, then $TARS_HOME, then ~/.tars."""
    env = os.environ.get("TARS_HOME")
    return Path(env) if env else home / ".tars"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".", help="the repo being installed into")
    ap.add_argument("--tars-home", help="tars home (default: $TARS_HOME, else ~/.tars) — pass what you pass arc as --tars_home")
    ap.add_argument("--home", help="the home whose ~/.arc and ~/.claude are read (default: $HOME)")
    ap.add_argument("--arc", default="arc", help="the arc binary to probe (default: arc on PATH)")
    ap.add_argument("--stage", action="append", help="only these stage ids (repeatable)")
    ap.add_argument("--roadmap", default=str(ROADMAP))
    a = ap.parse_args()

    home = Path(a.home) if a.home else Path.home()
    roadmap = json.loads(Path(a.roadmap).read_text())
    ctx = Ctx(repo=Path(a.repo).resolve(), home=home,
              tars_home=Path(a.tars_home) if a.tars_home else default_tars_home(home),
              arc=a.arc, roadmap=roadmap)
    stages = [s for s in roadmap["stages"] if not a.stage or s["id"] in a.stage]
    judged = [judge_stage(ctx, s) for s in stages]
    nxt = next((s["id"] for s in judged if not s["optional"] and not s["done"]), None)
    print(json.dumps({"repo": str(ctx.repo), "tars_home": str(ctx.tars_home), "stages": judged, "next": nxt},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
