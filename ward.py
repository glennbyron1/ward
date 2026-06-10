#!/usr/bin/env python3
"""Ward - scan a repo for employer/sensitive strings before they go public.

Modes (combinable):
  default     working tree + staged changes
  --history   every commit ever made (git log -p) - the deleted-file trap
  --path P    repo to scan (default: cwd)

Rules: ward-rules.txt next to this script (gitignored; copy from
ward-rules.example.txt). One pattern per line:
    plain text        -> case-insensitive substring
    re:<expression>   -> regex (case-insensitive)
    # comment / blank -> ignored

Exit 0 clean, 1 findings, 2 setup error. Pre-push hook relies on these.
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
SKIP_SELF = {"ward-rules.txt", "ward-rules.example.txt"}  # don't flag the rules
MAX_FILE_BYTES = 5 * 1024 * 1024


def load_rules(path: str) -> list[tuple[str, re.Pattern]]:
    if not os.path.exists(path):
        sys.exit(f"[ward] No rules file at {path}\n"
                 f"       cp ward-rules.example.txt ward-rules.txt  (then edit)")
    rules = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("re:"):
                rules.append((line, re.compile(line[3:], re.IGNORECASE)))
            else:
                rules.append((line, re.compile(re.escape(line), re.IGNORECASE)))
    if not rules:
        sys.exit("[ward] Rules file is empty - nothing to scan for.")
    return rules


def scan_text(text: str, rules, origin: str, findings: list) -> None:
    for n, line in enumerate(text.splitlines(), 1):
        for label, rx in rules:
            if rx.search(line):
                findings.append((origin, n, label, line.strip()[:120]))


def scan_tree(repo: str, rules, findings: list) -> None:
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f in SKIP_SELF:
                continue
            p = os.path.join(root, f)
            try:
                if os.path.getsize(p) > MAX_FILE_BYTES:
                    continue
                with open(p, errors="ignore") as fh:
                    scan_text(fh.read(), rules,
                              os.path.relpath(p, repo), findings)
            except OSError:
                continue


def git(repo: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", repo, *args],
                       capture_output=True, text=True)
    return r.stdout


def scan_staged(repo: str, rules, findings: list) -> None:
    scan_text(git(repo, "diff", "--cached"), rules, "STAGED-DIFF", findings)


def scan_history(repo: str, rules, findings: list) -> None:
    scan_text(git(repo, "log", "--all", "-p", "--no-color"),
              rules, "HISTORY", findings)


def main() -> None:
    ap = argparse.ArgumentParser(description="Ward - pre-push DLP scanner")
    ap.add_argument("--path", default=".", help="repo to scan")
    ap.add_argument("--history", action="store_true",
                    help="also scan full git history")
    ap.add_argument("--rules", default=os.path.join(HERE, "ward-rules.txt"))
    args = ap.parse_args()

    repo = os.path.abspath(args.path)
    rules = load_rules(args.rules)
    findings: list = []

    scan_tree(repo, rules, findings)
    if os.path.isdir(os.path.join(repo, ".git")):
        scan_staged(repo, rules, findings)
        if args.history:
            scan_history(repo, rules, findings)

    if findings:
        print(f"[ward] BLOCKED - {len(findings)} finding(s):\n")
        for origin, n, label, snippet in findings[:50]:
            print(f"  {origin}:{n}  [{label}]  {snippet}")
        if len(findings) > 50:
            print(f"  ... and {len(findings) - 50} more")
        if any(f[0] == "HISTORY" for f in findings):
            print("\n[ward] HISTORY hits: deleting the file is NOT enough - "
                  "scrub with git filter-repo before pushing anywhere public.")
        sys.exit(1)
    print("[ward] Clean. Safe to push.")


if __name__ == "__main__":
    main()
