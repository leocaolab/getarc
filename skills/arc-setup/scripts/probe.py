#!/usr/bin/env python3
"""Report where an arc install stands against roadmap.json — read-only.

Every criterion is judged from the world as it is now (files, PATH, git), so an
install that stopped half-way resumes by running this again. It changes nothing the
person wrote: the one arc command it runs in their repo, `arc rot --no-judge`, lets arc
create its own `.arc/.gitignore` and `.arc/tars/` (as every arc run does); `arc init`
runs only in a throwaway repo. It never prints a credential's value: for an env-var
credential it says only whether the variable is set.

Each stage belongs to one machine: `coding` (where the person writes code) or `pipeline`
(the machine that runs the server suite). `--machine` says which this run is on; a stage
of the other machine is listed with "judged_here": false and "done": null, because nothing
here can see it. On the coding machine the `client` and `first_pr` stages ask the board
what the pipeline serves, which is the pipeline's evidence from this side. Its HTTP
requests are GETs.

Output: one JSON object on stdout —
  {"machine", "stages": [{"id", "title", "machine", "judged_here", "optional", "done",
   "criteria": [{"id", "level", "ok", "says", "facts"}]}],
   "next": <first non-optional stage judged here and not done | null>}
"facts" carries what was seen (raw output, paths), so every answer arrives with its evidence.

What "ok" means:
  true   the fact was read and the criterion holds.
  false  the fact was read and the answer is no: a file or key is absent, a command
         that is the criterion exited non-zero, a server answered 4xx, a value read is
         not the one wanted.
  null   the fact could not be read, and facts["raw"] says why: a command could not
         run or gave no exit code, a command run to read the fact exited non-zero, a
         command's output does not carry the fact, a path could not be looked at or a
         file opened or decoded as UTF-8, a request went unanswered or the server failed
         (5xx), a body was not JSON or a file not TOML, something read has the wrong
         shape, or the probe cannot name what to ask about (no tenant name). null also
         marks a fact that cannot decide the criterion (a provider type with no fixed
         model family), and raw says so.
How the readers reach these answers (what a non-zero exit means, which silence is a no,
how every text is redacted) is stated in probe_core's docstring, next to the readers.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

# The sibling modules sit beside this script; `python3 -I` leaves its directory off the path.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe_core import Ctx, Verdict, scrubbed
from probe_coding import (
    arc_config_present,
    arc_has_verbs,
    arc_on_path,
    board_reachable,
    board_serves_repo,
    bridge_hooks,
    client_web_set,
    fixer_can_edit,
    fixer_cli_present,
    fixer_explicit,
    fixer_family_differs,
    gh_authed,
    git_repo,
    label_arc_hold,
    merge_yml_lists,
    merge_yml_on_target,
    merge_yml_present,
    no_providers_section,
    origin_remote,
    platform_ok,
    pr_landed,
    presubmit_on_target,
    presubmit_present,
    provider_auth_ready,
    python_toml,
    roles_resolve,
    rot_offline_runs,
    tars_config_parses,
    tars_config_present,
    tars_loads_in_arc,
)
from probe_pipeline import (
    board_answers_here,
    board_units_enabled,
    bridge_answers_here,
    delivery_one_build,
    git_new_enough,
    linger_on,
    machine_exposed,
    machine_toml_reads,
    release_declared,
    release_has_concurrency,
    release_job_lists,
    suite_on_path,
    tenant_check_passes,
    tenant_registered,
    tenant_reviewers_ready,
    tenant_routed,
    tenant_served_here,
    tenant_units_enabled,
)


ROADMAP = Path(__file__).resolve().parent.parent / "roadmap.json"
MACHINES = {"coding": {"coding"}, "pipeline": {"pipeline"}, "both": {"coding", "pipeline"}}
CHECKS: dict[str, Callable[[Ctx], Verdict]] = {
    "git_repo": git_repo, "platform": platform_ok, "python_toml": python_toml,
    "arc_on_path": arc_on_path, "arc_has_verbs": arc_has_verbs,
    "tars_config_present": tars_config_present, "tars_config_parses": tars_config_parses,
    "tars_loads_in_arc": tars_loads_in_arc, "provider_auth_ready": provider_auth_ready,
    "arc_config_present": arc_config_present, "no_providers_section": no_providers_section,
    "roles_resolve": roles_resolve, "fixer_explicit": fixer_explicit,
    "fixer_family_differs": fixer_family_differs, "fixer_can_edit": fixer_can_edit,
    "merge_yml_present": merge_yml_present,
    "merge_yml_lists": merge_yml_lists,
    "release_declared": release_declared, "release_job_lists": release_job_lists,
    "release_has_concurrency": release_has_concurrency, "delivery_one_build": delivery_one_build,
    "fixer_cli_present": fixer_cli_present, "bridge_hooks": bridge_hooks,
    "rot_offline_runs": rot_offline_runs, "origin_remote": origin_remote, "gh_authed": gh_authed,
    "presubmit_present": presubmit_present, "presubmit_on_target": presubmit_on_target,
    "merge_yml_on_target": merge_yml_on_target, "label_arc_hold": label_arc_hold,
    "suite_on_path": suite_on_path, "git_new_enough": git_new_enough, "linger_on": linger_on,
    "machine_toml_reads": machine_toml_reads, "machine_exposed": machine_exposed,
    "board_answers_here": board_answers_here, "bridge_answers_here": bridge_answers_here,
    "board_units_enabled": board_units_enabled,
    "tenant_registered": tenant_registered, "tenant_routed": tenant_routed,
    "tenant_reviewers_ready": tenant_reviewers_ready, "tenant_check_passes": tenant_check_passes,
    "tenant_served_here": tenant_served_here, "tenant_units_enabled": tenant_units_enabled,
    "client_web": client_web_set, "board_reachable": board_reachable, "board_serves_repo": board_serves_repo,
    "pr_landed": pr_landed,
}


def judge_stage(ctx: Ctx, stage: dict[str, Any]) -> dict[str, Any]:
    head = {"id": stage["id"], "title": stage["title"], "machine": stage["machine"],
            "optional": stage["optional"], "verify": stage["verify"]}
    if stage["machine"] not in ctx.machines:
        elsewhere = {"raw": f"judged on the {stage['machine']} machine: run probe.py --machine {stage['machine']} there"}
        return {**head, "judged_here": False, "done": None,
                "criteria": [{"id": c["id"], "level": c["level"], "says": c["says"], "ok": None, "facts": elsewhere}
                             for c in stage["criteria"]]}
    criteria = []
    for c in stage["criteria"]:
        v = CHECKS[c["id"]](ctx)
        criteria.append({"id": c["id"], "level": c["level"], "says": c["says"], "ok": v.ok, "facts": scrubbed(v.facts)})
    done = all(c["ok"] is True for c in criteria if c["level"] == "required")
    return {**head, "judged_here": True, "done": done, "criteria": criteria}


def default_tars_home(home: Path) -> Path:
    """Return the tars home in arc's own order: --tars_home, then $TARS_HOME, then ~/.tars."""
    env = os.environ.get("TARS_HOME")
    return Path(env) if env else home / ".tars"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".", help="the repo being installed into")
    ap.add_argument("--tars-home", help="tars home (default: $TARS_HOME, else ~/.tars) — pass what you pass arc as --tars_home")
    ap.add_argument("--home", help="the home whose ~/.arc and ~/.claude are read (default: $HOME)")
    ap.add_argument("--arc", default="arc", help="the arc binary to probe (default: arc on PATH)")
    ap.add_argument("--machine", choices=sorted(MACHINES), default="coding",
                    help="the machine this run is on: coding (default), pipeline, or both when one machine is both")
    ap.add_argument("--tenant", help="the repo's owner/name, for the pipeline stages (default: --repo's origin)")
    ap.add_argument("--stage", action="append", help="only these stage ids (repeatable)")
    ap.add_argument("--roadmap", default=str(ROADMAP))
    a = ap.parse_args()

    home = Path(a.home) if a.home else Path.home()
    roadmap = json.loads(Path(a.roadmap).read_text())
    ctx = Ctx(repo=Path(a.repo).resolve(), home=home,
              tars_home=Path(a.tars_home) if a.tars_home else default_tars_home(home),
              arc=a.arc, roadmap=roadmap, machines=MACHINES[a.machine], tenant=a.tenant)
    stages = [s for s in roadmap["stages"] if not a.stage or s["id"] in a.stage]
    judged = [judge_stage(ctx, s) for s in stages]
    nxt = next((s["id"] for s in judged if s["judged_here"] and not s["optional"] and not s["done"]), None)
    print(json.dumps({"repo": str(ctx.repo), "tars_home": str(ctx.tars_home), "machine": a.machine,
                      "stages": judged, "next": nxt},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
