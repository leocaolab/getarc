#!/usr/bin/env python3
"""List the Rust types a range of commits added — and did not just move or rename — grouped by kind.

    find_new_types.py [BASE] [HEAD] [--tests]
    find_new_types.py --all [HEAD]          # every type at HEAD (the whole repo)

BASE defaults to the merge-base of origin/main and HEAD, HEAD to HEAD; `--all` diffs from the empty tree. A type counts as new when
its definition line is added in BASE..HEAD and no definition of the same kind and name is removed
in the same range (a move or a re-indent shows up as both). Test files (`*tests.rs`, `tests/`,
testkits) and types inside an inline `#[cfg(test)] mod` are left out unless `--tests`;
a definition written inside a string literal (a parser fixture) is never a type and is always left out. Associated types (`type Error;` inside a trait or impl) are not
aliases and are left out.

For each type: kind, name, file:line at HEAD, and its doc comment and definition as written —
what the reader needs to answer "what is it", without anyone paraphrasing it — and every field typed
with a primitive (`String`, `PathBuf`, `&str`, integers), each a place to ask "is there a domain type for this?".
"""
import re
import subprocess
import sys
from collections import defaultdict

WEAK = re.compile(r"\b(String|PathBuf|&'?[a-z]*\s*str|i64|u64|i32|u32|usize|&Path)\b")
FIELD = re.compile(r"\s*(pub(\([a-z: ]+\))?\s+)?[a-z_][A-Za-z0-9_]*\s*:|\s*[A-Z][A-Za-z0-9]*\s*[({]")
DEF = re.compile(r"^\s*(?:pub(?:\([a-z: ]+\))?\s+)?(struct|enum|trait|type)\s+([A-Z][A-Za-z0-9_]*)")
KIND_ORDER = ["enum", "struct", "trait", "type"]


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def is_test(path):
    return path.endswith("tests.rs") or "/tests/" in path or "testkit" in path


def is_fixture(source):
    """A definition inside a string literal: `"struct A {}\n\\` or a block closed by `";` / `"#;`."""
    return "\\n\\" in source or source.rstrip().endswith(('";', '"#;', '"#'))


def changed_defs(base, head, sign):
    """(kind, name) -> [(path, line_at_head)] of definitions added (sign '+') or removed ('-')."""
    out = defaultdict(list)
    path, line = None, 0
    for raw in git("diff", "-M", "-U0", f"{base}..{head}", "--", "*.rs").splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            line = int(re.search(r"\+(\d+)", raw).group(1))
        elif raw.startswith(("+", "-")) and not raw.startswith(("+++", "---")):
            m = DEF.match(raw[1:])
            if raw[0] == sign and m and not is_associated(raw[1:]):
                out[(m.group(1), m.group(2))].append((path, line))
            if raw[0] == "+":
                line += 1
    return out


def is_associated(text):
    """`type Error;` / `type Error = X;` indented inside a trait or impl."""
    return bool(re.match(r"^\s{4,}type\s", text))


def in_test_module(head, path, line):
    """Defined inside an inline `#[cfg(test)] mod …` block."""
    lines = git("show", f"{head}:{path}").splitlines()
    indent = len(lines[line - 1]) - len(lines[line - 1].lstrip())
    for i in range(line - 2, -1, -1):
        text = lines[i]
        if text.strip() and len(text) - len(text.lstrip()) < indent and re.match(r"\s*(pub\s+)?mod\s", text):
            return i > 0 and lines[i - 1].strip() == "#[cfg(test)]"
    return False


def source_of(head, path, line):
    """The type's doc comment, attributes and definition, as written at HEAD."""
    lines = git("show", f"{head}:{path}").splitlines()
    top = line - 1
    while top > 0 and lines[top - 1].strip().startswith(("///", "#[")):
        top -= 1
    block, depth, opened = [], 0, False
    for text in lines[line - 1 :]:
        block.append(text)
        depth += text.count("{") - text.count("}")
        opened = opened or "{" in text
        if (opened and depth <= 0) or (not opened and text.rstrip().endswith(";")):
            break
    return "\n".join(lines[top : line - 1] + block)


def weak_fields(source):
    """Fields / variant payloads typed with a primitive (String, PathBuf, &str, integers) —
    each one a place to ask: is there a domain type for this?"""
    return [line.strip() for line in source.splitlines()
            if not line.strip().startswith(("///", "#[", "//")) and FIELD.match(line) and WEAK.search(line)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tests = "--tests" in sys.argv
    if "--all" in sys.argv:
        head = args[0] if args else "HEAD"
        base = git("hash-object", "-w", "-t", "tree", "/dev/null").strip()
    else:
        head = args[1] if len(args) > 1 else "HEAD"
        base = args[0] if args else git("merge-base", "origin/main", head).strip()

    added, removed = changed_defs(base, head, "+"), changed_defs(base, head, "-")
    new = {k: v for k, v in added.items() if k not in removed}
    grouped = defaultdict(list)
    for (kind, name), places in new.items():
        for path, line in places:
            if path and (tests or not (is_test(path) or in_test_module(head, path, line))):
                if not is_fixture(source_of(head, path, line)):
                    grouped[kind].append((name, path, line))

    total = sum(len(v) for v in grouped.values())
    print(f"# New types in {base[:9]}..{head}: {total}\n")
    for kind in KIND_ORDER:
        if not grouped[kind]:
            continue
        print(f"## {kind} ({len(grouped[kind])})\n")
        for name, path, line in sorted(grouped[kind]):
            source = source_of(head, path, line)
            print(f"### {name}\n\n`{path}:{line}`\n\n```rust\n{source}\n```\n")
            weak = weak_fields(source)
            if weak:
                print("weak-typed: " + " · ".join(f"`{w}`" for w in weak) + "\n")
        print()


if __name__ == "__main__":
    main()
