"""Hold the probe's vocabulary and its readers: verdicts and the kinds of unknown, commands,
files, HTTP, TOML and key lookups, and `shown`, the one way any text reaches the report.

Every reader returns a verdict in the probe's three values: true, the fact was read and
holds; false, the fact was read and the answer is no; null (unknown), the fact could not
be read, with facts["raw"] saying why and an `Unread` naming the kind. The readers carry
that rule so a check passes a verdict on rather than building its own false:
`read_file`, `read_toml`, `get_json`, `table_at` and every reader built on them return a
`Read`, the value they read with the verdict to give when that value is None; `lookup`
returns a value, or the unknown that names a key of the wrong shape; `judge_reply` judges
an HTTP `Reply`: 200 is yes, another status below 500 is no, no answer or a 5xx unknown.

`run` returns a `Ran`: the exit code (None when there was none), stdout and stderr. What a
non-zero exit means depends on the command's job. When the command is the criterion
(`arc workflow --list`, `gh auth status`, `arc rot`, `git cat-file -e`, a binary's
`--version`), a non-zero exit is a no: `Ran.verdict`. When the command only reads the
fact the criterion is judged from (`gh label list`, `loginctl show-user`, `git --version`,
`arc-server tenant url web`, the scratch `git init`), a non-zero exit means the probe
could not ask, which is unknown: `Ran.unanswered`. A command whose exit code is its
documented answer is judged by that code: `git remote get-url` exits 2 when the remote
does not exist, and `systemctl is-enabled` is judged by the state it prints per unit.

A check turns an unknown into false only where the silence is itself the answer it asks
for (whether the board or the bridge answers, whether a file parses), and does so by
naming the kind of unknown: `silence_is_no`. Every text in the output passes through
`shown`, which drops lines that carry a credential and cuts the text to a budget.
"""

from __future__ import annotations

import http.client
import json
import platform
import re
import stat
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Iterable


try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # older python3: the TOML checks report "cannot decide"
    tomllib = None  # type: ignore[assignment]


HTTP_TIMEOUT_SECS = 5
COMMAND_TIMEOUT_SECS = 60
# A line that carries a credential is never kept in a fact: a `token: …` / `secret = …` style
# assignment (`gh auth status` prints `Token: gho_…`), a value with a known token prefix, or a
# URL with a password in it.
CREDENTIAL_LINE = re.compile(
    r"(?i)(?:token|secret|password|api_?key)['\"]?\s*[:=]"
    r"|(?:gh[pousr]_|github_pat_|xox[abpr]-|sk-)[A-Za-z0-9_-]{8,}"
    r"|://[^/\s:@]*:[^/\s@]+@"
)
# How much of a text a fact keeps, from its end: a command's whole output, the raw words of a
# failure, and a short excerpt (a reply body, one line of stderr).
OUTPUT_TAIL_CHARS = 1200
RAW_TAIL_CHARS = 600
EXCERPT_CHARS = 300


@dataclass
class Ctx:
    repo: Path
    home: Path
    tars_home: Path
    arc: str
    roadmap: dict[str, Any]
    machines: set[str] = field(default_factory=lambda: {"coding"})
    tenant: str | None = None
    cache: dict[str, Any] = field(default_factory=dict)


class Unread(Enum):
    """Name why a fact could not be read; the name stays inside the probe, and `raw` carries the words."""

    NO_EXIT = auto()  # a command could not start, timed out, or was killed by a signal
    COMMAND_FAILED = auto()  # a command run to read the fact, not one that is the criterion, exited non-zero
    UNREADABLE_OUTPUT = auto()  # a command answered, but its output does not carry the fact (no state per unit, no version)
    NO_ANSWER = auto()  # nothing answered the request
    SERVER_ERROR = auto()  # the server answered 5xx: it failed to produce the fact
    NOT_JSON = auto()  # a body or a command's output is not JSON
    NOT_TOML = auto()  # a file is not TOML
    NO_TOML_READER = auto()  # this python has no tomllib, so no TOML file can be read
    UNREADABLE_FILE = auto()  # a path could not be looked at, or a file could not be opened or decoded as UTF-8
    WRONG_SHAPE = auto()  # something read has another shape than the one asked for (a key's value, a directory, an answer)
    NO_SUBJECT = auto()  # the probe cannot name what to ask about (no tenant name, no origin/HEAD, no USER)


@dataclass
class Verdict:
    ok: bool | None
    facts: dict[str, Any]
    unread: Unread | None = None


def unknown(why: Unread, facts: dict[str, Any]) -> Verdict:
    return Verdict(None, facts, why)


def all_known(outcomes: Iterable[bool | None]) -> bool | None:
    """Return the three-valued AND: False if any is False, else None if any is unknown, else True."""
    seen = list(outcomes)
    if False in seen:
        return False
    return None if None in seen else True


@dataclass(frozen=True)
class Ran:
    """Hold what a command did; `exit` is None when it gave no exit code."""

    exit: int | None
    out: str
    err: str

    @property
    def said(self) -> str:
        return (self.out + self.err).strip()

    def succeeded(self) -> bool | None:
        return None if self.exit is None else self.exit == 0

    def verdict(self, facts: dict[str, Any]) -> Verdict:
        """Judge a command that is the criterion by its exit code: 0 is yes, another code is no, no code is unknown."""
        if self.exit is None:
            return unknown(Unread.NO_EXIT, {**facts, "raw": shown(self.said, RAW_TAIL_CHARS)})
        if self.exit == 0:
            return Verdict(True, facts)
        return Verdict(False, {**facts, "exit": self.exit, "raw": shown(self.said, RAW_TAIL_CHARS)})

    def unanswered(self, asked: str, facts: dict[str, Any]) -> Verdict | None:
        """Return the unknown to give when `asked`, a command run to read a fact, did not answer; None when it exited 0."""
        if self.exit == 0:
            return None
        why, how = (Unread.NO_EXIT, "gave no exit code") if self.exit is None else (Unread.COMMAND_FAILED, f"failed (exit {self.exit})")
        return unknown(why, {**facts, "exit": self.exit, "raw": f"{asked} {how}: {shown(self.said, RAW_TAIL_CHARS)}"})


def run(argv: list[str], cwd: Path | None = None, timeout: int = COMMAND_TIMEOUT_SECS) -> Ran:
    """Run a read-only command with no stdin, so a command that would prompt answers as if no one is there.

    Its output is decoded as UTF-8 with each byte that does not decode replaced, so a tool that
    prints another encoding still gives a Ran.
    """
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
    except OSError as e:
        return Ran(None, "", f"{' '.join(argv)}: {e}")
    except subprocess.TimeoutExpired:
        return Ran(None, "", f"timed out after {timeout}s: {' '.join(argv)}")
    if p.returncode < 0:
        return Ran(None, p.stdout, f"{p.stderr}killed by signal {-p.returncode}: {' '.join(argv)}")
    return Ran(p.returncode, p.stdout, p.stderr)


def shown(value: Any, n: int = OUTPUT_TAIL_CHARS) -> str:
    """Render `value` as text a fact may carry: drop each line that carries a credential, keep the last `n` characters.

    A value that is not a string is rendered with repr first. Every text reaches the output
    through here: checks call it to cut a value down where they quote it, and `scrubbed`
    passes every string of every fact through it again before the report is printed.
    """
    text = value if isinstance(value, str) else repr(value)
    kept = "\n".join(line for line in text.splitlines() if not CREDENTIAL_LINE.search(line))
    return kept if len(kept) <= n else "…" + kept[-n:]


@dataclass(frozen=True)
class Read:
    """Hold a value read from the world with its verdict; `value` is None exactly when the verdict says why it is not there."""

    value: Any
    verdict: Verdict


def file_present(path: Path) -> Verdict:
    """Judge whether `path` is a regular file; absent is a no, a failed look or something else there is unknown."""
    facts = {"path": str(path)}
    try:
        mode = path.stat().st_mode
    except FileNotFoundError:
        return Verdict(False, {**facts, "raw": f"{path} does not exist"})
    except OSError as e:
        return unknown(Unread.UNREADABLE_FILE, {**facts, "raw": f"{path} could not be looked at: {e}"})
    if not stat.S_ISREG(mode):
        what = "a directory" if stat.S_ISDIR(mode) else "not a regular file"
        return unknown(Unread.WRONG_SHAPE, {**facts, "raw": f"{path} is {what}, not a file"})
    return Verdict(True, facts)


def read_file(path: Path) -> Read:
    """Read a text file; it is judged first as `file_present` does, then one that cannot be read as UTF-8 is unknown."""
    v = file_present(path)
    if v.ok is not True:
        return Read(None, v)
    try:
        return Read(path.read_text(encoding="utf-8"), v)
    except (OSError, UnicodeDecodeError) as e:
        return Read(None, unknown(Unread.UNREADABLE_FILE, {**v.facts, "raw": f"{path} could not be read: {e}"}))


def read_toml(path: Path) -> Read:
    """Read a TOML file as `read_file` does; a file that is not TOML is unknown."""
    facts = {"path": str(path)}
    if tomllib is None:
        return Read(None, unknown(Unread.NO_TOML_READER, {**facts, "raw": f"python {platform.python_version()} has no tomllib (needs 3.11+)"}))
    text = read_file(path)
    if text.value is None:
        return text
    try:
        return Read(tomllib.loads(text.value), Verdict(True, facts))
    except tomllib.TOMLDecodeError as e:
        return Read(None, unknown(Unread.NOT_TOML, {**facts, "raw": f"{path} is not TOML: {e}"}))


SHAPES = {dict: "a table", list: "a list", str: "a string", bool: "true or false"}


def lookup(table: dict[str, Any], keys: tuple[str, ...], kind: type, default: Any, where: str) -> tuple[Any, Verdict | None]:
    """Return the value at `keys` through nested tables, or `default` when a key on the way is absent.

    A key that exists with a value of another shape gives no value and an unknown verdict naming it.
    """
    node: Any = table
    for depth, key in enumerate(keys):
        if key not in node:
            return default, None
        node = node[key]
        want = kind if depth == len(keys) - 1 else dict
        if not isinstance(node, want):
            dotted = ".".join(keys[: depth + 1])
            return None, unknown(Unread.WRONG_SHAPE, {"raw": f"{where}: `{dotted}` is {shown(repr(node), EXCERPT_CHARS)}, not {SHAPES[want]}"})
    return node, None


def table_at(read: Read, key: str) -> Read:
    """Return the table at `key` of a TOML read; an absent file or key reads as an empty table."""
    if read.value is None:
        return Read({}, read.verdict) if read.verdict.ok is False else read
    value, bad = lookup(read.value, (key,), dict, {}, read.verdict.facts["path"])
    return Read(None, bad) if bad else Read(value, read.verdict)


def tables_in(read: Read, key: str, what: str) -> Read:
    """Return the table at `key` whose every value is itself a table (`what` names one), as `table_at` does."""
    found = table_at(read, key)
    if found.value is None:
        return found
    odd = sorted(k for k, x in found.value.items() if not isinstance(x, dict))
    if odd:
        return Read(None, unknown(Unread.WRONG_SHAPE, {"raw": f"{found.verdict.facts['path']}: {what} {shown(odd, EXCERPT_CHARS)} are not tables"}))
    return found


@dataclass(frozen=True)
class Reply:
    """Hold an HTTP answer; `status` is None when nothing answered, and `body` then says why."""

    status: int | None
    body: str


def get(url: str) -> Reply:
    """Send a GET to `url` with no proxy."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=HTTP_TIMEOUT_SECS) as r:
            return Reply(r.status, r.read().decode(errors="replace"))
    except urllib.error.HTTPError as e:
        return Reply(e.code, error_body(e))
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as e:
        return Reply(None, f"GET {url}: {e!r}")


def error_body(e: urllib.error.HTTPError) -> str:
    """Read an error reply's body, or say why it could not be read; its status has already answered."""
    try:
        return e.read().decode(errors="replace")
    except (http.client.HTTPException, OSError, ValueError) as err:
        return f"the body of the {e.code} reply could not be read: {err!r}"


def judge_reply(reply: Reply, facts: dict[str, Any]) -> Verdict:
    """Judge an HTTP reply: 200 is yes, another 2xx-4xx is no, no answer or a 5xx is unknown."""
    facts = {**facts, "status": reply.status}
    if reply.status is None:
        return unknown(Unread.NO_ANSWER, {**facts, "raw": shown(reply.body, RAW_TAIL_CHARS)})
    if reply.status >= 500:
        return unknown(Unread.SERVER_ERROR, {**facts, "raw": shown(reply.body, RAW_TAIL_CHARS)})
    if reply.status != 200:
        return Verdict(False, {**facts, "raw": shown(reply.body, RAW_TAIL_CHARS)})
    return Verdict(True, facts)


def silence_is_no(v: Verdict) -> Verdict:
    """Turn no answer into the answer no, for a check whose question is whether something answers."""
    return Verdict(False, v.facts) if v.unread is Unread.NO_ANSWER else v


def get_json(url: str) -> Read:
    """Fetch `url` as JSON, judged as `judge_reply` does; a 200 body that is not JSON is unknown."""
    reply = get(url)
    v = judge_reply(reply, {"url": url})
    if v.ok is not True:
        return Read(None, v)
    try:
        return Read(json.loads(reply.body), v)
    except json.JSONDecodeError as e:
        return Read(None, unknown(Unread.NOT_JSON, {**v.facts, "raw": f"not JSON ({e}): {shown(reply.body, EXCERPT_CHARS)}"}))


def scrubbed(value: Any) -> Any:
    """Return `value` with every string in it, keys included and however deep, passed through `shown`."""
    if isinstance(value, str):
        return shown(value)
    if isinstance(value, dict):
        return {shown(k): scrubbed(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrubbed(v) for v in value]
    return value
