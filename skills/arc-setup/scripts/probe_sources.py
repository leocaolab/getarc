"""Read the files and answers both machines' checks judge from: the tars and arc configs,
origin's name, and the board's /api/machine answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from probe_core import (
    Ctx,
    EXCERPT_CHARS,
    Ran,
    Read,
    Unread,
    Verdict,
    all_known,
    get_json,
    lookup,
    read_toml,
    run,
    shown,
    silence_is_no,
    table_at,
    tables_in,
    unknown,
)


def tars(ctx: Ctx) -> Read:
    if "tars" not in ctx.cache:
        ctx.cache["tars"] = read_toml(ctx.tars_home / "config.toml")
    return ctx.cache["tars"]


def providers(ctx: Ctx) -> Read:
    """Return the tars [providers.<id>] tables; no tars file is no providers."""
    return tables_in(tars(ctx), "providers", "[providers.<id>]")


def arc_config(ctx: Ctx) -> Read:
    if "arc_config" not in ctx.cache:
        ctx.cache["arc_config"] = read_toml(ctx.repo / ".arc" / "config.toml")
    return ctx.cache["arc_config"]


def roles_in(read: Read) -> Read:
    """Return a config's [roles] as role → provider id; no file or no [roles] is no roles."""
    found = table_at(read, "roles")
    if found.value is None:
        return found
    odd = sorted(k for k, x in found.value.items() if not isinstance(x, str))
    if odd:
        return Read(None, unknown(Unread.WRONG_SHAPE, {"raw": f"{found.verdict.facts['path']}: [roles] {shown(odd, EXCERPT_CHARS)} are not provider ids"}))
    return found


def roles(ctx: Ctx) -> Read:
    return roles_in(arc_config(ctx))


@dataclass(frozen=True)
class Provider:
    """Hold the tars provider a [roles] entry resolves to: the role, the provider's id, its `type` and its table."""

    role: str
    pid: str
    kind: str
    table: dict[str, Any]


def provider_type(pid: str, p: dict[str, Any]) -> Read:
    """Return a provider's `type`; absent is a no, a value that is not a string is unknown and names the key."""
    kind, bad = lookup(p, ("type",), str, None, f"[providers.{pid}]")
    if bad:
        return Read(None, bad)
    if kind is None:
        return Read(None, Verdict(False, {"raw": f"[providers.{shown(pid, EXCERPT_CHARS)}] has no `type`"}))
    return Read(kind, Verdict(True, {}))


def role_provider(r: dict[str, str], ps: dict[str, dict[str, Any]], names: tuple[str, ...]) -> Read:
    """Resolve the first of `names` that [roles] sets to the tars provider it names.

    A role [roles] does not set, and an id tars does not define, are a no; a provider whose
    `type` is absent is a no and one whose `type` is not a string is unknown; each says which.
    """
    role = next((n for n in names if n in r), None)
    if role is None:
        return Read(None, Verdict(False, {"raw": f"[roles] sets none of {', '.join(names)}"}))
    pid = r[role]
    if pid not in ps:
        return Read(None, Verdict(False, {"role": role, "provider": pid,
                                          "raw": f"[roles] {role} = {shown(repr(pid), EXCERPT_CHARS)}, which tars does not define "
                                                 f"(it defines: {shown(', '.join(sorted(ps)), EXCERPT_CHARS) or 'none'})"}))
    kind = provider_type(pid, ps[pid])
    if kind.value is None:
        v = kind.verdict
        return Read(None, Verdict(v.ok, {"role": role, "provider": pid, **v.facts}, v.unread))
    return Read(Provider(role, pid, kind.value, ps[pid]), Verdict(True, {"role": role, "provider": pid, "type": kind.value}))


# `git remote get-url`'s exit code when the remote does not exist (git-remote(1)).
NO_SUCH_REMOTE = 2


def origin_name(ctx: Ctx) -> Read:
    """Return origin's owner/name; no origin, or a URL naming none, is a no."""
    ran = run(["git", "remote", "get-url", "origin"], cwd=ctx.repo)
    if ran.exit == NO_SUCH_REMOTE:
        return Read(None, ran.verdict({}))
    if not_asked := ran.unanswered("git remote get-url origin", {}):
        return Read(None, not_asked)
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", ran.out.strip())
    if m is None:
        return Read(None, Verdict(False, {"raw": f"origin's URL {shown(repr(ran.out.strip()), EXCERPT_CHARS)} names no owner/name"}))
    name = f"{m.group(1)}/{m.group(2)}"
    return Read(name, Verdict(True, {"origin": name}))


def board_answer_problem(answer: Any) -> str | None:
    """Return what makes a /api/machine answer unreadable (crates/infra/types/src/machine_wire.rs), or None."""
    if not isinstance(answer, dict):
        return f"the answer is {type(answer).__name__}, not an object"
    machine = answer.get("machine")
    if machine is not None and not (isinstance(machine, dict) and isinstance(machine.get("bridge"), str)):
        return f"`machine` is {shown(repr(machine), EXCERPT_CHARS)}, not null or an object with a `bridge` address"
    tenants = answer.get("tenants")
    if not isinstance(tenants, list):
        return f"`tenants` is {shown(repr(tenants), EXCERPT_CHARS)}, not a list"
    for t in tenants:
        bad = (not isinstance(t, dict) or not isinstance(t.get("name"), str)
               or not isinstance(t.get("former_names", []), list) or not isinstance(t.get("stores"), dict)
               or not all(isinstance(t["stores"].get(s), bool) for s in ("merge", "review"))
               or not isinstance(t.get("home_exists"), bool))
        if bad:
            return (f"a tenant is {shown(repr(t), EXCERPT_CHARS)}, not an object with a `name`, `former_names` list, "
                    "`stores` object with true-or-false `merge` and `review`, and `home_exists`")
    return None


def served(answer: dict[str, Any], name: str, asked: dict[str, Any]) -> Verdict:
    """Judge whether a readable /api/machine answer serves `name` with its merge and review stores open."""
    tenants = answer["tenants"]
    hit = next((t for t in tenants if t["name"] == name or name in t.get("former_names", [])), None)
    facts = {**asked, "tenant": name, "board_tenants": [t["name"] for t in tenants],
             "refused": answer.get("refused", []), "clashing": answer.get("clashing", [])}
    if hit is None:
        return Verdict(False, facts)
    stores = hit["stores"]
    facts |= {"home": hit.get("home"), "home_exists": hit["home_exists"], "stores": stores}
    return Verdict(hit["home_exists"] and stores["merge"] and stores["review"], facts)


def asked_board(found: Read) -> Read:
    """Ask the board `found` names for /api/machine; return its readable answer, or None and the verdict to give."""
    if found.value is None:
        return found
    answer = get_json(found.value + "/api/machine")
    if answer.value is None:
        return answer
    problem = board_answer_problem(answer.value)
    if problem is not None:
        return Read(None, unknown(Unread.WRONG_SHAPE, {**answer.verdict.facts, "raw": f"the board's answer is malformed: {problem}"}))
    return answer


def board_answers(found: Read) -> Verdict:
    """Judge whether the board answers /api/machine; here silence is itself the answer no."""
    return silence_is_no(asked_board(found).verdict)


# arc's refusal when a workflow has several jobs and none is named (infra_workflow WorkflowError::AmbiguousJob).
# Its wording is pinned by infra_workflow's test
# `several_jobs_with_none_named_are_refused_in_the_words_the_setup_probe_reads`; emitting the jobs as data is b/3442.
SEVERAL_JOBS = re.compile(r"defines several jobs — name the job to run, one of: (.+)$", re.M)


def planned(ctx: Ctx, rel: str, job: str | None) -> Ran:
    """Ask arc to plan `job` of the workflow at `rel`, or its only job when `job` is None; nothing runs."""
    named = ["--job", job] if job else []
    return run([ctx.arc, "workflow", rel, *named, "--list", "--repo", str(ctx.repo)], cwd=ctx.repo)


def jobs_arc_names(ran: Ran) -> list[str] | None:
    """Return the jobs arc lists when it refuses to pick one of several; None when it said anything else."""
    m = SEVERAL_JOBS.search(ran.said) if ran.exit not in (None, 0) else None
    return [job.strip() for job in m.group(1).split(",")] if m else None


def list_jobs(ctx: Ctx, rel: str, jobs: list[str]) -> Verdict:
    ran = {job: planned(ctx, rel, job) for job in jobs}
    results = {job: {"exit": r.exit, "output": shown(r.said)} for job, r in ran.items()}
    return Verdict(all_known(r.succeeded() for r in ran.values()), {"file": rel, "jobs": results})


def every_job_plans(ctx: Ctx, rel: str) -> Verdict:
    """Ask arc to plan every job of the workflow at `rel`: its only job, or each job arc names when it has several."""
    whole = planned(ctx, rel, None)
    jobs = jobs_arc_names(whole)
    if jobs is None:
        return whole.verdict({"file": rel, "output": shown(whole.said)})
    return list_jobs(ctx, rel, jobs)
