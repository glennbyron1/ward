# Ward — Pre-Push DLP for Public Repos

A protective boundary between private context and public code. Ward scans a repo for employer-identifying or sensitive strings **before** anything is pushed — working tree, staged changes, and (critically) **git history**, because a deleted file is still published if it was ever committed.

Born from a real workflow: personal open-source tools that an employer also deploys. The code is public; the employer's names, IPs, hostnames, and docs must never be. Ward enforces that line instead of trusting memory.

## Why history matters (the trap most people miss)

`git push` publishes the **entire commit history**, not the current files.
Deleting a sensitive file in a later commit does NOT unpublish it.
Ward's `--history` mode greps every commit ever made, so the filing cabinet
gets checked, not just the desk.

## Design: your real rules are themselves secret

The patterns you scan for (employer names, internal hostnames, IP ranges)
would leak information if published. So:

- `ward-rules.txt`        — your REAL rules. **Gitignored. Never committed.**
- `ward-rules.example.txt` — sanitized placeholder rules, safe to publish.

Same code/config separation as everything else in the lab: the tool is public,
the site-specific config is not.

## Usage

```bash
cp ward-rules.example.txt ward-rules.txt   # then edit with real patterns
python3 ward.py                  # scan working tree + staged (default)
python3 ward.py --history        # also sweep all git history (slower, thorough)
python3 ward.py --path ~/repo    # scan a different repo
```

Exit code 0 = clean, 1 = findings (which is what makes the hook work).

## Enforce it: the pre-push hook

```bash
./install-hook.sh ~/path/to/repo     # installs .git/hooks/pre-push
```

After this, `git push` in that repo runs Ward automatically and **refuses to
push** on any finding. The control no longer depends on remembering.

## Defense-in-depth (Ward is the backstop, not the only line)

1. **Prevent:** keep private docs outside the repo, or in a gitignored folder.
2. **Enforce:** the pre-push hook blocks anything that slips through.
3. **Audit:** occasional `--history` runs catch anything that predates the rules.

## Honest scope

- Pattern matching (case-insensitive substrings + regex), not ML. It catches
  what you tell it to catch — keep the rules file current.
- Complements, not replaces, general secret scanners (gitleaks/trufflehog find
  API keys and credentials; Ward finds *your employer*). Run both if you like.
- A `--history` hit requires `git filter-repo` to actually scrub — Ward finds,
  it does not rewrite.
