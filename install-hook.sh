#!/usr/bin/env bash
# install-hook.sh <repo-path> — make `git push` run Ward and block on findings.
set -euo pipefail
REPO="${1:?usage: ./install-hook.sh /path/to/repo}"
WARD="$(cd "$(dirname "$0")" && pwd)/ward.py"
HOOK="$REPO/.git/hooks/pre-push"
[ -d "$REPO/.git" ] || { echo "Not a git repo: $REPO"; exit 2; }
cat > "$HOOK" << HOOK_EOF
#!/usr/bin/env bash
# Installed by Ward — refuses to push if the scan finds anything.
exec python3 "$WARD" --path "$REPO"
HOOK_EOF
chmod +x "$HOOK"
echo "Ward pre-push hook installed at $HOOK"
