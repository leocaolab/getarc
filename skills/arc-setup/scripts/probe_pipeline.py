"""Judge the criteria of the pipeline machine's stages (suite through release), one function
per criterion id in roadmap.json.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

from probe_core import (
    Ctx,
    EXCERPT_CHARS,
    RAW_TAIL_CHARS,
    Ran,
    Read,
    Unread,
    Verdict,
    all_known,
    file_present,
    get,
    judge_reply,
    lookup,
    read_toml,
    run,
    shown,
    silence_is_no,
    table_at,
    tables_in,
    unknown,
)
from probe_sources import (
    arc_config,
    asked_board,
    board_answers,
    list_jobs,
    origin_name,
    planned,
    providers,
    role_provider,
    roles_in,
    served,
)


# A basic / react reviewer on the pipeline asks for critic_l4, which falls back to default.
REVIEWER_ROLES = ("critic_l4", "default")
MODEL_REVIEWERS = {"basic", "react"}
# arc-server refuses to start below this git (crates/apps/server/src/boot.rs GIT_FLOOR).
GIT_FLOOR = (2, 38)


def machine_toml_path(ctx: Ctx) -> Path:
    return ctx.home / ".arc" / "machine.toml"


def machine_toml(ctx: Ctx) -> Read:
    if "machine_toml" not in ctx.cache:
        ctx.cache["machine_toml"] = read_toml(machine_toml_path(ctx))
    return ctx.cache["machine_toml"]


def server(ctx: Ctx, *args: str) -> Ran:
    """Run `arc-server <args>` on the machine.toml of the home being probed."""
    return run(["arc-server", *args, "--config", str(machine_toml_path(ctx))])


NO_TENANT_NAME = "no tenant name: pass --tenant owner/name, or --repo a clone whose origin names it"


def tenant_name(ctx: Ctx) -> Read:
    """Return the tenant this run asks about; with no name the pipeline's tenant facts cannot be asked for."""
    if ctx.tenant:
        return Read(ctx.tenant, Verdict(True, {"tenant": ctx.tenant}))
    name = origin_name(ctx)
    if name.value is None:
        v = name.verdict
        return Read(None, unknown(v.unread or Unread.NO_SUBJECT, {**v.facts, "raw": f"{NO_TENANT_NAME} ({shown(v.facts.get('raw'), EXCERPT_CHARS)})"}))
    return name


def tenant_table(ctx: Ctx) -> Read:
    """Return this repo's [[tenant]] table; machine.toml without one is a no."""
    named = tenant_name(ctx)
    if named.value is None:
        return named
    name = named.value
    machine = machine_toml(ctx)
    if machine.value is None:
        v = machine.verdict
        return Read(None, Verdict(v.ok, {**v.facts, "tenant": name}, v.unread))
    path = machine.verdict.facts["path"]
    tenants, bad = lookup(machine.value, ("tenant",), list, [], path)
    if bad:
        return Read(None, bad)
    if not all(isinstance(t, dict) for t in tenants):
        return Read(None, unknown(Unread.WRONG_SHAPE, {"tenant": name, "raw": f"{path}: `tenant` is {shown(repr(tenants), EXCERPT_CHARS)}, not a list of [[tenant]] tables"}))
    facts = {"tenant": name, "tenants": [t.get("name") for t in tenants]}
    found = next((t for t in tenants if t.get("name") == name), None)
    return Read(found, Verdict(found is not None, facts))


def routes_of(tenant: dict[str, Any]) -> tuple[list[dict[str, Any]] | None, Verdict | None]:
    """Return the tenant's [[tenant.review.route]] rules; none is an empty list."""
    routes, bad = lookup(tenant, ("review", "route"), list, [], "the [[tenant]]")
    if bad:
        return None, bad
    if not all(isinstance(r, dict) for r in routes):
        return None, unknown(Unread.WRONG_SHAPE, {"raw": f"the [[tenant]]: `review.route` is {shown(repr(routes), EXCERPT_CHARS)}, not a list of [[tenant.review.route]] tables"})
    return routes, None


def git_version(text: str) -> tuple[int, int] | None:
    m = re.search(r"git version (\d+)\.(\d+)", text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def unclean_check_lines(output: str) -> list[str]:
    """Return the finding lines of `arc-server tenant check` that say neither ok nor skip."""
    return [line.strip() for line in output.splitlines() if re.match(r"^  (FAIL|warn) ", line)]


# The `is-enabled` state of a unit that starts at boot; enabled-runtime is gone after a reboot.
ENABLED = "enabled"


def units_enabled(units: list[str]) -> Verdict:
    """Ask systemd whether every unit is enabled; a reply without one state per unit is unknown.

    Each unit is judged by the state systemd prints for it: `is-enabled` exits 0 when any one
    of the units is enabled.
    """
    if shutil.which("systemctl") is None:
        return Verdict(None, {"raw": "no systemctl on this machine: no unit starts the services, so they run only while started by hand"})
    ran = run(["systemctl", "--user", "is-enabled", *units])
    states = ran.out.split()
    facts = {"units": dict(zip(units, states)), "exit": ran.exit}
    if ran.exit is None:
        return ran.verdict(facts)
    if len(states) != len(units):
        return unknown(Unread.UNREADABLE_OUTPUT, {**facts, "raw": f"systemctl printed no state per unit: {shown(ran.said, RAW_TAIL_CHARS)}"})
    off = [f"{unit} is {state}" for unit, state in zip(units, states) if state != ENABLED]
    if off:
        return Verdict(False, {**facts, "raw": "not enabled: " + ", ".join(off)})
    return Verdict(True, facts)


def unit_instance(name: str) -> str:
    """Return a tenant's systemd instance: its owner/name with `/` turned into `-`."""
    return name.replace("/", "-")


def local_web(ctx: Ctx) -> Read:
    """Return the board address `arc-server tenant url web` prints on this machine."""
    ran = server(ctx, "tenant", "url", "web")
    if not_asked := ran.unanswered("arc-server tenant url web", {}):
        return Read(None, not_asked)
    if not ran.out.strip():
        return Read(None, unknown(Unread.UNREADABLE_OUTPUT, {"raw": f"`arc-server tenant url web` printed no address: {shown(ran.said, RAW_TAIL_CHARS)}"}))
    return Read(ran.out.strip().rstrip("/"), Verdict(True, {"web": shown(ran.out.strip())}))


def release_table(ctx: Ctx) -> Read:
    """Return [release] with its `workflow` and `job` checked to be strings; none is an empty table."""
    release = table_at(arc_config(ctx), "release")
    if release.value is None:
        return release
    for key in ("workflow", "job"):
        _, bad = lookup(release.value, (key,), str, None, "[release]")
        if bad:
            return Read(None, bad)
    return release


def release_declared(ctx: Ctx) -> Verdict:
    release = release_table(ctx)
    if release.value is None:
        return release.verdict
    r = release.value
    return Verdict(bool(r.get("workflow")), {"release": r})


def release_job_lists(ctx: Ctx) -> Verdict:
    release = release_table(ctx)
    if release.value is None:
        return release.verdict
    r = release.value
    wf = r.get("workflow")
    if not wf:
        return Verdict(False, {"release": r, "raw": "[release] names no workflow"})
    job = r.get("job")
    if job:
        return list_jobs(ctx, wf, [job])
    ran = planned(ctx, wf, None)
    return ran.verdict({"file": wf, "output": shown(ran.said)})


# The line `arc workflow --list` prints for a group the job holds, its own or the file-wide one
# (infra_workflow exec/job.rs `announcement`); a group arc cannot read prints no "group".
# Its form is pinned by infra_workflow's test `a_held_group_is_announced_in_the_words_the_setup_probe_reads`;
# emitting the group as data is b/3442.
HOLDS_A_GROUP = re.compile(r"^\s*concurrency\s+group `", re.M)


def release_has_concurrency(ctx: Ctx) -> Verdict:
    release = release_table(ctx)
    if release.value is None:
        return release.verdict
    r = release.value
    wf = r.get("workflow")
    if not wf:
        return Verdict(False, {"raw": "[release] names no workflow"})
    ran = planned(ctx, wf, r.get("job"))
    facts = {"file": wf, "job": r.get("job"), "output": shown(ran.said)}
    if not ran.succeeded():
        return ran.verdict(facts)
    if HOLDS_A_GROUP.search(ran.out):
        return Verdict(True, facts)
    return Verdict(False, {**facts, "raw": f"arc plans the job holding no concurrency group, and a deploy refuses such a job: {shown(ran.said, RAW_TAIL_CHARS)}"})


def delivery_one_build(ctx: Ctx) -> Verdict:
    release = release_table(ctx)
    if release.value is None:
        return release.verdict
    r = release.value
    delivery = read_toml(ctx.repo / ".arc" / "delivery.toml")
    if delivery.value is None:
        return delivery.verdict
    builds = tables_in(delivery, "builds", "[builds.<id>]")
    if builds.value is None:
        return builds.verdict
    workflow = r.get("workflow")
    if not workflow:
        return Verdict(False, {"release": r, "raw": "[release] names no workflow, so no build can be matched to it"})
    same = [b for b, x in builds.value.items() if runs_release(x, workflow, r.get("job"))]
    return Verdict(len(same) == 1, {"builds_running_release": same, "release": r})


def runs_release(build: dict[str, Any], workflow: str, job: str | None) -> bool:
    """Judge whether a [builds.<id>] runs the release: it names the release's workflow, and its job when [release] names one."""
    return build.get("workflow") == workflow and (job is None or build.get("job") == job)


def suite_binary(binary: str) -> Verdict:
    """Judge one suite binary by whether its `--version` names it; `said` holds what it printed."""
    path = shutil.which(binary)
    if path is None:
        return Verdict(False, {"said": "not on PATH"})
    ran = run([path, "--version"])
    if ran.exit != 0:
        said = f"exit {ran.exit}: {shown(ran.said, EXCERPT_CHARS)}"
        return Verdict(ran.succeeded(), {"said": said}, Unread.NO_EXIT if ran.exit is None else None)
    line = ran.out.strip()
    return Verdict(line.startswith(binary + " "), {"said": shown(line, EXCERPT_CHARS)})


def suite_on_path(ctx: Ctx) -> Verdict:
    judged = {binary: suite_binary(binary) for binary in ctx.roadmap["suite_binaries"]}
    return Verdict(all_known(j.ok for j in judged.values()),
                   {"versions": {b: j.facts["said"] for b, j in judged.items()},
                    "not_working": [b for b, j in judged.items() if j.ok is False],
                    "unread": [b for b, j in judged.items() if j.ok is None]})


def git_new_enough(_: Ctx) -> Verdict:
    ran = run(["git", "--version"])
    if not_asked := ran.unanswered("git --version", {}):
        return not_asked
    found = git_version(ran.out)
    if found is None:
        return unknown(Unread.UNREADABLE_OUTPUT, {"raw": f"`git --version` printed no version: {shown(ran.said, RAW_TAIL_CHARS)}"})
    return Verdict(found >= GIT_FLOOR, {"git": shown(ran.out.strip(), EXCERPT_CHARS), "need": ".".join(map(str, GIT_FLOOR))})


def linger_on(_: Ctx) -> Verdict:
    if shutil.which("loginctl") is None:
        return Verdict(None, {"raw": "no loginctl on this machine (no systemd): nothing keeps the services up after logout or a reboot"})
    user = os.environ.get("USER") or os.environ.get("LOGNAME")
    if not user:
        return unknown(Unread.NO_SUBJECT, {"raw": "neither USER nor LOGNAME is set, so the user whose lingering to read cannot be determined"})
    ran = run(["loginctl", "show-user", user, "--property=Linger", "--value"])
    facts = {"user": user, "linger": shown(ran.out.strip(), EXCERPT_CHARS), "exit": ran.exit}
    if not_asked := ran.unanswered("loginctl show-user", facts):
        return not_asked
    return Verdict(ran.out.strip() == "yes", facts)


def machine_toml_reads(ctx: Ctx) -> Verdict:
    present = file_present(machine_toml_path(ctx))
    if present.ok is not True:
        return present
    ran = server(ctx, "tenant", "list")
    return ran.verdict({**present.facts, "exit": ran.exit, "output": shown(ran.said, RAW_TAIL_CHARS)})


def machine_exposed(ctx: Ctx) -> Verdict:
    machine = machine_toml(ctx)
    if machine.value is None:
        return machine.verdict
    where = machine.verdict.facts["path"]
    address, bad_address = lookup(machine.value, ("machine", "address"), str, None, where)
    expose, bad_expose = lookup(machine.value, ("machine", "expose"), bool, False, where)
    if bad_address or bad_expose:
        return bad_address or bad_expose
    return Verdict(bool(address) and expose, {"address": address, "expose": expose})


def board_answers_here(ctx: Ctx) -> Verdict:
    return board_answers(local_web(ctx))


def bridge_answers_here(ctx: Ctx) -> Verdict:
    answer = asked_board(local_web(ctx))
    if answer.value is None:
        return answer.verdict
    if answer.value.get("machine") is None:
        return Verdict(False, {**answer.verdict.facts, "raw": "the board names no chat server (its `machine` is null: it has no roster)"})
    bridge = answer.value["machine"]["bridge"]
    return silence_is_no(judge_reply(get(bridge.rstrip("/") + "/healthz"), {"bridge": bridge}))


def board_units_enabled(_: Ctx) -> Verdict:
    return units_enabled(["arc-web.service", "arc-bridge.service"])


def tenant_registered(ctx: Ctx) -> Verdict:
    tenant = tenant_table(ctx)
    if tenant.value is None:
        return tenant.verdict
    home, bad = absolute_path(tenant.value, ("home",), "the [[tenant]]")
    if bad:
        return Verdict(None, {**tenant.verdict.facts, **bad.facts}, bad.unread)
    return Verdict(True, {**tenant.verdict.facts, "home": str(home) if home else None})


def tenant_routed(ctx: Ctx) -> Verdict:
    tenant = tenant_table(ctx)
    if tenant.value is None:
        return tenant.verdict
    name = tenant.verdict.facts["tenant"]
    routes, bad = routes_of(tenant.value)
    if bad:
        return Verdict(None, {"tenant": name, **bad.facts}, bad.unread)
    return Verdict(bool(routes), {"tenant": name, "routes": routes})


def absolute_path(table: dict[str, Any], keys: tuple[str, ...], where: str) -> tuple[Path | None, Verdict | None]:
    """Return the path at `keys`, or None when absent; a relative one is the wrong shape, as arc-server types it an absolute path (config AbsPath)."""
    text, bad = lookup(table, keys, str, None, where)
    if bad or text is None:
        return None, bad
    if not Path(text).is_absolute():
        return None, unknown(Unread.WRONG_SHAPE, {"raw": f"{where}: `{'.'.join(keys)}` is {shown(repr(text), EXCERPT_CHARS)}, not an absolute path"})
    return Path(text), None


def model_config_of(tenant: dict[str, Any]) -> tuple[Path | None, Verdict | None]:
    """Return the file whose [roles] the tenant's model reviewers use; None when the tenant names none."""
    named, bad = absolute_path(tenant, ("review", "model_config"), "the [[tenant]]")
    home, bad_home = absolute_path(tenant, ("home",), "the [[tenant]]")
    if bad or bad_home:
        return None, bad or bad_home
    if named:
        return named, None
    return (home / ".arc" / "config.toml" if home else None), None


def tenant_reviewers_ready(ctx: Ctx) -> Verdict:
    found = tenant_table(ctx)
    if found.value is None:
        return found.verdict
    tenant = found.value
    routes, bad = routes_of(tenant)
    if bad:
        return bad
    models = sorted({str(r.get("reviewer")) for r in routes} & MODEL_REVIEWERS)
    if not models:
        return Verdict(True, {"model_reviewers": [], "why": "no route names a model reviewer, so none needs a provider"})
    config, bad = model_config_of(tenant)
    if bad:
        return bad
    if config is None:
        return Verdict(False, {"model_reviewers": models, "tenant": found.verdict.facts["tenant"],
                               "raw": "the [[tenant]] has no `home` (and no `review.model_config`), so its reviewers' [roles] file cannot be named"})
    read = read_toml(config)
    if read.value is None:
        v = read.verdict
        return Verdict(v.ok, {"model_reviewers": models, **v.facts}, v.unread)
    r = roles_in(read)
    if r.value is None:
        return r.verdict
    ps = providers(ctx)
    if ps.value is None:
        return ps.verdict
    resolved = role_provider(r.value, ps.value, REVIEWER_ROLES).verdict
    return Verdict(resolved.ok, {"model_reviewers": models, "config": str(config), "tars": str(ctx.tars_home / "config.toml"),
                                 **resolved.facts}, resolved.unread)


def tenant_check_passes(ctx: Ctx) -> Verdict:
    named = tenant_name(ctx)
    if named.value is None:
        return named.verdict
    name = named.value
    ran = server(ctx, "tenant", "check", name)
    not_ok = unclean_check_lines(ran.out)
    lines = [shown(line, EXCERPT_CHARS) or "a FAIL or warn line that mentions a token (not shown)" for line in not_ok]
    judged = ran.verdict({"exit": ran.exit, "not_ok": lines, "output": shown(ran.said)})
    if judged.ok is True and not_ok:
        return Verdict(False, {**judged.facts, "raw": "; ".join(lines)})
    return judged


def tenant_served_here(ctx: Ctx) -> Verdict:
    answer = asked_board(local_web(ctx))
    if answer.value is None:
        return answer.verdict
    named = tenant_name(ctx)
    if named.value is None:
        return named.verdict
    return served(answer.value, named.value, answer.verdict.facts)


def tenant_units_enabled(ctx: Ctx) -> Verdict:
    named = tenant_name(ctx)
    if named.value is None:
        return named.verdict
    name = named.value
    inst = unit_instance(name)
    return units_enabled([f"arc-server@{inst}.service", f"arc-review@{inst}.service"])
