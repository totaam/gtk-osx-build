#!/usr/bin/env python3
"""Create gtk-osx-build PR branches and copy module updates by id."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCOPES = ("modulesets-stable", "modulesets", "modulesets-unstable")


def run(repo: Path, *args: str) -> None:
    subprocess.run(args, cwd=repo, check=True)


def out(repo: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=repo, text=True).strip()


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def module_pattern(ident: str) -> re.Pattern[str]:
    quoted = re.escape(ident)
    return re.compile(
        r'<(?P<tag>[A-Za-z0-9_+.-]+)\b(?=[^>]*\bid="' + quoted + r'")[^>]*>.*?</(?P=tag)>',
        re.S,
    )


def find_block(path: Path, ident: str) -> str | None:
    text = path.read_text()
    matches = list(module_pattern(ident).finditer(text))
    if not matches:
        return None
    if len(matches) != 1:
        raise RuntimeError(f"{path}:{ident}: expected one module block, found {len(matches)}")
    return matches[0].group(0)


def block_is_versioned(block: str) -> bool:
    return bool(re.search(r"<branch\b[^>]*\bversion=", block, re.S))


def replace_block(path: Path, ident: str, block: str) -> bool:
    text = path.read_text()
    matches = list(module_pattern(ident).finditer(text))
    if not matches:
        return False
    if len(matches) != 1:
        raise RuntimeError(f"{path}:{ident}: expected one module block, found {len(matches)}")
    target_block = matches[0].group(0)
    if not block_is_versioned(target_block):
        return False
    if target_block == block:
        return False
    match = matches[0]
    path.write_text(text[: match.start()] + block + text[match.end() :])
    ET.parse(path)
    return True


def moduleset_files(repo: Path, scope: str) -> list[Path]:
    directory = repo / scope
    if not directory.exists():
        return []
    return sorted(directory.glob("*.modules"))


def source_blocks(source: Path, ident: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    stable_block: str | None = None
    for scope in SCOPES:
        for path in moduleset_files(source, scope):
            block = find_block(path, ident)
            if block and block_is_versioned(block):
                blocks[scope] = block
                if scope == "modulesets-stable":
                    stable_block = block
    if stable_block:
        for scope in SCOPES:
            blocks.setdefault(scope, stable_block)
    return blocks


def ensure_branch(target: Path, branch: str, amend: bool) -> None:
    if amend:
        run(target, "git", "switch", branch)
    else:
        run(target, "git", "switch", "master")
        run(target, "git", "switch", "-c", branch)


def touched_status_clean(target: Path, rels: set[str]) -> None:
    if not rels:
        return
    status = subprocess.check_output(["git", "-C", str(target), "status", "--short", "--", *sorted(rels)], text=True)
    dirty = [line for line in status.splitlines() if line and not line.startswith("?? ")]
    if dirty:
        raise RuntimeError("tracked moduleset changes already present:\n" + "\n".join(dirty))


def apply_updates(source: Path, target: Path, ids: list[str]) -> tuple[set[str], list[str]]:
    touched: set[str] = set()
    skipped: list[str] = []
    for ident in ids:
        blocks = source_blocks(source, ident)
        if not blocks:
            skipped.append(f"{ident}: no versioned source block")
            continue
        any_applied = False
        for scope in SCOPES:
            block = blocks.get(scope)
            if not block:
                continue
            for path in moduleset_files(target, scope):
                target_block = find_block(path, ident)
                if target_block is None:
                    continue
                if not block_is_versioned(target_block):
                    skipped.append(f"{ident}: {path.relative_to(target)} is unversioned")
                    continue
                if replace_block(path, ident, block):
                    touched.add(str(path.relative_to(target)))
                    any_applied = True
        if not any_applied:
            skipped.append(f"{ident}: no applicable changes")
    return touched, skipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--ids", required=True)
    parser.add_argument("--commit-subject", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--amend", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    ids = parse_csv(args.ids)
    rel_candidates = {str(p.relative_to(args.target)) for scope in SCOPES for p in moduleset_files(args.target, scope)}
    touched_status_clean(args.target, rel_candidates)
    ensure_branch(args.target, args.branch, args.amend)
    touched, skipped = apply_updates(args.source, args.target, ids)
    if not touched:
        raise SystemExit("no files changed")
    for rel in sorted(touched):
        ET.parse(args.target / rel)
    run(args.target, "git", "diff", "--check", "--", *sorted(touched))
    run(args.target, "git", "add", "--", *sorted(touched))
    if args.amend:
        run(args.target, "git", "commit", "--amend", "--no-edit")
    else:
        run(args.target, "git", "commit", "-m", args.commit_subject)
    commit = out(args.target, "git", "rev-parse", "--short", "HEAD")
    if args.push:
        if args.amend:
            run(args.target, "git", "push", "--force-with-lease", args.remote, args.branch)
        else:
            run(args.target, "git", "push", "-u", args.remote, args.branch)
    print(f"commit\t{commit}")
    for rel in sorted(touched):
        print(f"touched\t{rel}")
    for item in skipped:
        print(f"skipped\t{item}")
    if args.push:
        print(f"pr\thttps://github.com/totaam/gtk-osx-build/pull/new/{args.branch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
