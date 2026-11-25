"""Judge the criteria of the coding machine's stages (prereq through first_pr), one function
per criterion id in roadmap.json.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from probe_core import (
    Ctx,
    EXCERPT_CHARS,
    RAW_TAIL_CHARS,
    Read,
    Unread,
    Verdict,
    all_known,
    file_present,
    get_json,
    lookup,
    read_file,
    read_toml,
    run,
    shown,
    tomllib,
    unknown,
)
from probe_sources import (
    arc_config,
    asked_board,
    board_answers,
    every_job_plans,
    origin_name,
    Provider,
    provider_type,
    providers,
    role_provider,
    roles,
    served,
    tars,
)


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
# Where a tars secret can come from (tars-types secret.rs `SecretRef`).
SECRET_SOURCES = {"inline", "env", "file"}
KNOWN_TYPES = {
    "openai", "openai_compat", "anthropic", "gemini", "bedrock", "vllm", "mlx",
    "llamacpp", "claude_cli", "claude_sdk", "codex_cli", "opencode", "antigravity",
}
CRITIC_ROLES = ("critic_l4", "critic", "default")
HOLD_LABEL = "arc-hold"
# The most labels one `gh label list --search` answer may hold; a full page cannot prove absence.
LABEL_PAGE = 100
# `arc rot --no-judge` walks the whole repo, which takes minutes on a large one.
ROT_TIMEOUT_SECS = 300
# How many of the board's latest merge rounds pr_landed shows, newest first.
RECENT_ROUNDS_SHOWN = 5


def provider_executable(pid: str, p: dict[str, Any], kind: str | None) -> tuple[str | None, Verdict | None]:
    """Return the executable a provider runs: its own `executable`, else its CLI type's default."""
    exe, bad = lookup(p, ("executable",), str, None, f"[providers.{pid}]")
    if bad:
        return None, bad
    return exe or CLI_EXECUTABLE.get(kind or ""), None


def default_branch(ctx: Ctx) -> Read:
    """Return origin's default branch as `origin/<name>` (as of the last fetch); without it nothing can be looked up."""
    ran = run(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"], cwd=ctx.repo)
    if ran.exit is None:
        return Read(None, unknown(Unread.NO_EXIT, {"raw": f"origin/HEAD could not be read: {shown(ran.said, RAW_TAIL_CHARS)}"}))
    if ran.exit != 0 or not ran.out.strip().startswith("origin/"):
        return Read(None, unknown(Unread.NO_SUBJECT, {"raw": f"{shown(ran.said, RAW_TAIL_CHARS)} — origin/HEAD is not set (`git remote set-head origin --auto` sets it)"}))
    return Read(ran.out.strip(), Verdict(True, {}))


def on_default_branch(ctx: Ctx, rel: str) -> Verdict:
    branch = default_branch(ctx)
    if branch.value is None:
        return branch.verdict
    ran = run(["git", "cat-file", "-e", f"{branch.value}:{rel}"], cwd=ctx.repo)
    return ran.verdict({"branch": branch.value, "file": rel, "as_of": "the last git fetch"})


def client_web(ctx: Ctx) -> Read:
    """Return the board ~/.arc/client.toml names."""
    client = read_toml(ctx.home / ".arc" / "client.toml")
    if client.value is None:
        return client
    path = client.verdict.facts["path"]
    web, bad = lookup(client.value, ("web",), str, None, path)
    if bad:
        return Read(None, bad)
    if web is None or not web.strip():
        return Read(None, Verdict(False, {"path": path, "web": web, "raw": "client.toml names no `web`"}))
    return Read(web.rstrip("/"), Verdict(True, {"path": path, "web": web}))


def merger_problem(answer: Any) -> str | None:
    """Return what makes a /api/r/<owner>/<name>/merger answer unreadable (merge/store/src/read.rs), or None."""
    if not isinstance(answer, dict):
        return f"the answer is {type(answer).__name__}, not an object"
    metrics = answer.get("metrics")
    if not isinstance(metrics, dict):
        return f"`metrics` is {shown(repr(metrics), EXCERPT_CHARS)}, not an object"
    landed = metrics.get("landed")
    if not isinstance(landed, int) or isinstance(landed, bool):
        return f"`metrics.landed` is {shown(repr(landed), EXCERPT_CHARS)}, not a count"
    recent = answer.get("recent", [])
    if not isinstance(recent, list) or not all(isinstance(a, dict) for a in recent):
        return f"`recent` is {shown(repr(recent), EXCERPT_CHARS)}, not a list of rounds"
    return None


def git_repo(ctx: Ctx) -> Verdict:
    ran = run(["git", "rev-parse", "--show-toplevel"], cwd=ctx.repo)
    return ran.verdict({"toplevel": shown(ran.out.strip())} if ran.exit == 0 else {})


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
    ran = run([path, "--version"])
    return ran.verdict({"path": path, "version": shown(ran.said, EXCERPT_CHARS)})


def arc_has_verbs(ctx: Ctx) -> Verdict:
    path = shutil.which(ctx.arc)
    if path is None:
        return Verdict(False, {"raw": "arc is not on PATH"})
    verbs = ctx.roadmap["required_verbs"]
    ran = {verb: run([path, verb, "--help"]) for verb in verbs}
    missing = {verb: f"exit {r.exit}: {shown(r.err.strip(), EXCERPT_CHARS)}" for verb, r in ran.items() if r.succeeded() is False}
    unread = {verb: shown(r.said, EXCERPT_CHARS) for verb, r in ran.items() if r.succeeded() is None}
    ok = all_known(r.succeeded() for r in ran.values())
    if ok is True:
        return Verdict(True, {"verbs": verbs})
    return Verdict(ok, {"missing": missing, "unread": unread}, Unread.NO_EXIT if ok is None else None)


def tars_config_present(ctx: Ctx) -> Verdict:
    return file_present(ctx.tars_home / "config.toml")


def tars_config_parses(ctx: Ctx) -> Verdict:
    config = tars(ctx)
    if config.value is None:
        v = config.verdict
        return Verdict(False, v.facts) if v.unread is Unread.NOT_TOML else v
    ps = providers(ctx)
    if ps.value is None:
        return ps.verdict
    typed = {pid: provider_type(pid, p) for pid, p in ps.value.items()}
    shapeless = next((t.verdict for t in typed.values() if t.verdict.ok is None), None)
    if shapeless:
        return shapeless
    listed = {pid: {"type": t.value, "default_model": ps.value[pid].get("default_model"), "family": FAMILY.get(t.value or "")}
              for pid, t in typed.items()}
    unknown_type = [pid for pid, t in typed.items() if t.value not in KNOWN_TYPES]
    return Verdict(bool(listed) and not unknown_type, {"providers": listed, "unknown_type": unknown_type})


# The line `arc init` writes for each tars provider id it found into .arc/config.toml.example
# (apps_cli init.rs `render_example_config`). Its form is pinned by apps_cli's test
# `the_example_lists_each_tars_id_on_the_line_the_setup_probe_reads`; emitting the ids as data is b/3442.
EXAMPLE_PROVIDER_ID = re.compile(r"^#   - (\S+)$", re.M)


def tars_loads_in_arc(ctx: Ctx) -> Verdict:
    """Let arc itself read the tars config: `arc init` in a throwaway git repo.

    arc lists the tars providers before it notices there is no terminal, so a malformed
    file fails here with tars's own words, and a readable one leaves an example naming
    the ids arc found. The throwaway repo is deleted; the person's repo is not touched.
    """
    with tempfile.TemporaryDirectory(prefix="arc-install-probe-") as tmp:
        scratch = run(["git", "init", "-q", tmp])
        if not_asked := scratch.unanswered("git init of a scratch repo", {}):
            return not_asked
        ran = run([ctx.arc, "--tars_home", str(ctx.tars_home), "--repo", tmp, "init"])
        if ran.exit is None:
            return ran.verdict({})
        example = read_file(Path(tmp) / ".arc" / "config.toml.example")
        if example.verdict.ok is None:
            return example.verdict
        ids = EXAMPLE_PROVIDER_ID.findall(example.value or "")
        return Verdict(bool(ids), {"exit": ran.exit, "ids_arc_sees": ids, "arc_said": shown(ran.said)})


def provider_auth(pid: str, p: dict[str, Any]) -> Verdict:
    """Judge one provider's credential; `seen` says what was found."""
    where = f"[providers.{pid}]"
    source, bad = lookup(p, ("auth", "secret", "source"), str, None, where)
    secret, bad_secret = lookup(p, ("auth", "secret"), dict, None, where)
    var, bad_var = lookup(p, ("auth", "secret", "var"), str, None, where)
    path, bad_path = lookup(p, ("auth", "secret", "path"), str, None, where)
    value, bad_value = lookup(p, ("auth", "secret", "value"), str, None, where)
    kind = provider_type(pid, p)
    exe, bad_exe = provider_executable(pid, p, kind.value)
    bad_kind = kind.verdict if kind.verdict.ok is None else None
    shape = next((b for b in (bad, bad_secret, bad_var, bad_path, bad_value, bad_kind, bad_exe) if b), None)
    if shape:
        return Verdict(None, {"seen": shape.facts["raw"]}, shape.unread)
    if secret is not None and source not in SECRET_SOURCES:
        named = "names no `auth.secret.source`" if source is None else f"`auth.secret.source` is {shown(repr(source), EXCERPT_CHARS)}"
        return unknown(Unread.WRONG_SHAPE, {"seen": f"{where}: {named}, not one of {sorted(SECRET_SOURCES)}"})
    if source == "inline":
        if value is None:
            return Verdict(False, {"seen": f"{where}: `auth.secret.source` is inline but `auth.secret.value` is missing"})
        return Verdict(True, {"seen": "an inline secret in the tars config (its value is not shown)"})
    if source == "env":
        if var is None:
            return Verdict(False, {"seen": f"{where}: `auth.secret.source` is env but `auth.secret.var` is missing"})
        is_set = bool(os.environ.get(var))
        return Verdict(is_set, {"seen": f"env var {var} is {'set' if is_set else 'NOT set in this shell'}"})
    if source == "file":
        if path is None:
            return Verdict(False, {"seen": f"{where}: `auth.secret.source` is file but `auth.secret.path` is missing"})
        key = file_present(Path(os.path.expanduser(path)))
        said = "exists" if key.ok else key.facts["raw"]
        return Verdict(key.ok, {"seen": f"key file {key.facts['path']}: {said}"}, key.unread)
    if exe:
        found = shutil.which(exe)
        return Verdict(found is not None, {"seen": f"executable {exe}: {found or 'NOT on PATH'}"})
    return Verdict(True, {"seen": "no credential named (auth kind none, or none needed)"})


def provider_auth_ready(ctx: Ctx) -> Verdict:
    ps = providers(ctx)
    if ps.value is None:
        return ps.verdict
    if not ps.value:
        return Verdict(None, {"raw": "no providers to check"})
    judged = {pid: provider_auth(pid, p) for pid, p in ps.value.items()}
    return Verdict(all_known(j.ok for j in judged.values()), {"providers": {pid: j.facts["seen"] for pid, j in judged.items()}})


def arc_config_present(ctx: Ctx) -> Verdict:
    v = file_present(ctx.repo / ".arc" / "config.toml")
    return Verdict(v.ok, {**v.facts, "example_present": file_present(ctx.repo / ".arc" / "config.toml.example").ok}, v.unread)


def no_providers_section(ctx: Ctx) -> Verdict:
    cfg = arc_config(ctx)
    if cfg.value is None:
        return cfg.verdict
    found = cfg.value.get("providers")
    return Verdict("providers" not in cfg.value, {"providers": sorted(found) if isinstance(found, dict) else found})


def roles_resolve(ctx: Ctx) -> Verdict:
    cfg = arc_config(ctx)
    if cfg.value is None:
        return cfg.verdict
    found = roles_and_providers(ctx)
    if isinstance(found, Verdict):
        return found
    r, ps = found
    critic = role_provider(r, ps, CRITIC_ROLES)
    judged = [critic.verdict, *(role_provider(r, ps, (role,)).verdict for role in r)]
    faults = [v.facts["raw"] for v in judged if v.ok is not True]
    facts = {"roles": r, "critic": critic.value.pid if critic.value else None, "tars_ids": sorted(ps)}
    return Verdict(all_known(v.ok for v in judged), {**facts, "raw": "; ".join(dict.fromkeys(faults))} if faults else facts)


def roles_and_providers(ctx: Ctx) -> tuple[dict[str, str], dict[str, dict[str, Any]]] | Verdict:
    """Return [roles] and the tars providers, or the verdict of whichever could not be had."""
    r, ps = roles(ctx), providers(ctx)
    if r.value is None or ps.value is None:
        return r.verdict if r.value is None else ps.verdict
    return r.value, ps.value


def fixer_explicit(ctx: Ctx) -> Verdict:
    r = roles(ctx)
    if r.value is None:
        return r.verdict
    return Verdict("fixer" in r.value, {"fixer": r.value.get("fixer")})


def fixer_provider(ctx: Ctx) -> Provider | Verdict:
    """Return the provider [roles] names as the fixer, or the verdict that says why there is none."""
    found = roles_and_providers(ctx)
    if isinstance(found, Verdict):
        return found
    fixer = role_provider(*found, ("fixer",))
    return fixer.verdict if fixer.value is None else fixer.value


def fixer_family_differs(ctx: Ctx) -> Verdict:
    found = roles_and_providers(ctx)
    if isinstance(found, Verdict):
        return found
    r, ps = found
    critic, fixer = role_provider(r, ps, CRITIC_ROLES), role_provider(r, ps, ("fixer",))
    if critic.value is None or fixer.value is None:
        return critic.verdict if critic.value is None else fixer.verdict
    pair = {"critic": critic.value, "fixer": fixer.value}
    fam = {k: FAMILY.get(p.kind) for k, p in pair.items()}
    facts = {"critic": critic.value.pid, "fixer": fixer.value.pid, "families": fam,
             "models": {k: p.table.get("default_model") for k, p in pair.items()}}
    familyless = [f"{p.pid} is {p.kind}" for p in pair.values() if FAMILY.get(p.kind) is None]
    if familyless:
        return Verdict(None, {**facts, "raw": f"a provider type with no fixed family ({', '.join(familyless)}) — ask which model family it serves"})
    return Verdict(fam["critic"] != fam["fixer"], facts)


def fixer_can_edit(ctx: Ctx) -> Verdict:
    found = fixer_provider(ctx)
    if isinstance(found, Verdict):
        return found
    fixer = found
    facts = {"fixer": fixer.pid, "type": fixer.kind}
    if fixer.kind == "claude_cli":
        tools = fixer.table.get("tools", "disabled")
        return Verdict(tools != "disabled", {**facts, "tools": tools})
    if fixer.kind == "codex_cli":
        sandbox = fixer.table.get("sandbox", "read-only")
        return Verdict(sandbox == "workspace-write", {**facts, "sandbox": sandbox})
    return Verdict(None, {**facts, "raw": f"the fixer {fixer.pid} is a {fixer.kind} provider; only a claude_cli or codex_cli fixer has a setting to check"})


MERGE_YML = ".github/workflows/merge.yml"


def merge_yml_present(ctx: Ctx) -> Verdict:
    return file_present(ctx.repo / MERGE_YML)


def merge_yml_lists(ctx: Ctx) -> Verdict:
    return every_job_plans(ctx, MERGE_YML)


def fixer_cli_present(ctx: Ctx) -> Verdict:
    found = fixer_provider(ctx)
    if isinstance(found, Verdict):
        return found
    fixer = found
    exe, bad = provider_executable(fixer.pid, fixer.table, fixer.kind)
    if bad:
        return bad
    if exe is None:
        return Verdict(None, {"type": fixer.kind, "raw": f"the fixer {fixer.pid} is a {fixer.kind} provider, not an agent CLI"})
    path = shutil.which(exe)
    return Verdict(path is not None, {"executable": exe, "path": path})


def client_web_set(ctx: Ctx) -> Verdict:
    return client_web(ctx).verdict


def board_reachable(ctx: Ctx) -> Verdict:
    return board_answers(client_web(ctx))


def board_serves_repo(ctx: Ctx) -> Verdict:
    answer = asked_board(client_web(ctx))
    if answer.value is None:
        return answer.verdict
    name = origin_name(ctx)
    if name.value is None:
        return name.verdict
    return served(answer.value, name.value, answer.verdict.facts)


def bridge_hooks(ctx: Ctx) -> Verdict:
    places = [ctx.repo / ".claude" / "settings.json", ctx.repo / ".claude" / "settings.local.json",
              ctx.home / ".claude" / "settings.json", ctx.repo / ".codex" / "config.toml",
              ctx.home / ".codex" / "config.toml", ctx.repo / ".agents" / "hooks.json",
              ctx.home / ".gemini" / "config" / "hooks.json"]
    read = {p: read_file(p) for p in places}
    found = [str(p) for p, got in read.items() if got.value is not None and "arc bridge hook" in got.value]
    unreadable = {str(p): got.verdict.facts["raw"] for p, got in read.items() if got.verdict.ok is None}
    if found:
        return Verdict(True, {"files_with_hooks": found})
    if unreadable:
        return unknown(Unread.UNREADABLE_FILE, {"files_with_hooks": [], "raw": "; ".join(unreadable.values())})
    return Verdict(False, {"files_with_hooks": []})


def rot_offline_runs(ctx: Ctx) -> Verdict:
    ran = run([ctx.arc, "rot", "--no-judge", "--repo", str(ctx.repo)], cwd=ctx.repo, timeout=ROT_TIMEOUT_SECS)
    return ran.verdict({"exit": ran.exit, "output": shown(ran.said)})


def origin_remote(ctx: Ctx) -> Verdict:
    return origin_name(ctx).verdict


def gh_authed(ctx: Ctx) -> Verdict:
    ran = run(["gh", "auth", "status"])
    return ran.verdict({"output": shown(ran.said, RAW_TAIL_CHARS)})


def presubmit_present(ctx: Ctx) -> Verdict:
    return file_present(ctx.repo / "presubmit.toml")


def presubmit_on_target(ctx: Ctx) -> Verdict:
    return on_default_branch(ctx, "presubmit.toml")


def merge_yml_on_target(ctx: Ctx) -> Verdict:
    return on_default_branch(ctx, MERGE_YML)


def label_arc_hold(ctx: Ctx) -> Verdict:
    ran = run(["gh", "label", "list", "--search", HOLD_LABEL, "--json", "name", "--limit", str(LABEL_PAGE)], cwd=ctx.repo)
    if not_asked := ran.unanswered("gh label list", {}):
        return not_asked
    try:
        listed = json.loads(ran.out)
    except json.JSONDecodeError as e:
        return unknown(Unread.NOT_JSON, {"raw": f"gh label list printed no JSON ({e}): {shown(ran.out, EXCERPT_CHARS)}"})
    if not isinstance(listed, list) or not all(isinstance(x, dict) and isinstance(x.get("name"), str) for x in listed):
        return unknown(Unread.WRONG_SHAPE, {"raw": f"gh label list printed JSON that is not a list of labels with a `name`: {shown(ran.out, EXCERPT_CHARS)}"})
    names = [label["name"] for label in listed]
    if HOLD_LABEL in names:
        return Verdict(True, {"labels_found": names})
    if len(names) >= LABEL_PAGE:
        return Verdict(None, {"labels_found": len(names),
                              "raw": f"the search filled its page of {LABEL_PAGE} without `{HOLD_LABEL}`, so a later page may hold it"})
    return Verdict(False, {"labels_found": names})


def pr_landed(ctx: Ctx) -> Verdict:
    web = client_web(ctx)
    if web.value is None:
        return web.verdict
    name = origin_name(ctx)
    if name.value is None:
        return name.verdict
    answer = get_json(f"{web.value}/api/r/{name.value}/merger")
    if answer.value is None:
        return answer.verdict
    asked = answer.verdict.facts
    problem = merger_problem(answer.value)
    if problem is not None:
        return unknown(Unread.WRONG_SHAPE, {**asked, "raw": f"the board's merge record is malformed: {problem}"})
    metrics = answer.value["metrics"]
    recent = [{k: a.get(k) for k in ("pr", "outcome", "why", "base_fail")}
              for a in answer.value.get("recent", [])[:RECENT_ROUNDS_SHOWN]]
    return Verdict(metrics["landed"] >= 1, {**asked, "metrics": metrics, "recent": recent})
