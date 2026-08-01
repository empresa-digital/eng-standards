#!/usr/bin/env bash
#
# PR pre-review bot — runs the eng-standards reviewer + architecture pass on a
# GitHub PR, classifies it SAFE vs NEEDS_HUMAN (fail-closed), and prints a
# ready-to-post comment. With --post it publishes the comment on the PR.
#
# Auth: locally, relies on your existing `claude` login (nothing to set). In CI,
# pass a Claude Code *plan* OAuth token as CLAUDE_CODE_OAUTH_TOKEN so runs stay on
# the plan rather than the metered API. Do NOT export that token globally on a dev
# machine — the CLI reads it and it can shadow your interactive login (e.g. `/usage`).
#
# Usage:
#   review/pr-bot/run.sh <owner/repo> <pr-number> [--post]
#
# Env overrides:
#   ENG_DIR        rule library root         (default: ~/.cache/eng-standards)
#   REPO_DIR       local checkout to review  (default: ~/projects/<repo-basename>)
#   ORG_PROFILE    org yaml under orgs/       (default: empresa-digital.yaml)
#   MODEL          model for the review pass  (default: opus)
#
set -euo pipefail

REPO="${1:?usage: run.sh <owner/repo> <pr-number> [--post]}"
PR="${2:?usage: run.sh <owner/repo> <pr-number> [--post]}"
POST="${3:-}"

ENG_DIR="${ENG_DIR:-$HOME/.cache/eng-standards}"
REPO_DIR="${REPO_DIR:-$HOME/projects/$(basename "$REPO")}"
ORG_PROFILE="${ORG_PROFILE:-empresa-digital.yaml}"
# Reviews are important, so they're worth Opus.
MODEL="${MODEL:-opus}"

# Auth: use CLAUDE_CODE_OAUTH_TOKEN when provided (e.g. CI, keeps runs on the plan);
# otherwise fall back to the machine's existing `claude` login. Never require it.
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && export CLAUDE_CODE_OAUTH_TOKEN

# The bot's language and its fixed comment strings live in the org profile, so this
# shared tool carries no company- or language-specific text. Fall back to generic
# English when a profile does not define meta.pr_review.
load_cfg() {
  python3 - "$ENG_DIR/orgs/$ORG_PROFILE" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1])) or {}
pr = ((d.get("meta") or {}).get("pr_review") or {})
c = pr.get("comment") or {}
def g(k, dflt): return c.get(k) or dflt
print(pr.get("language") or "English")
print(g("title", "🤖 **Automated pre-review** — eng-standards · *experimental*"))
print(g("details_summary", "Full review"))
print(g("safe_header", "✅ **Considered safe to merge without extra review.**"))
print(g("needs_human_header", "🔴 **Human review required before merge.**"))
print(g("reasons_label", "Reasons:"))
print(g("footer", "_Automation under test; may still be noisy. Feedback helps calibrate._"))
PY
}
mapfile -t CFG < <(load_cfg)
PR_REVIEW_LANG="${CFG[0]}"; C_TITLE="${CFG[1]}"; C_SUMMARY="${CFG[2]}"
C_SAFE="${CFG[3]}"; C_NEEDS="${CFG[4]}"; C_REASONS="${CFG[5]}"; C_FOOTER="${CFG[6]}"

WORK="$(mktemp -d)"
WT="$WORK/worktree"
DIFF_FILE="$WORK/pr.diff"
META_FILE="$WORK/pr.meta"
OUT_FILE="$WORK/review.md"
cleanup() { git -C "$REPO_DIR" worktree remove --force "$WT" 2>/dev/null || true; rm -rf "$WORK"; }
trap cleanup EXIT

echo ">> fetching PR #$PR of $REPO" >&2
gh pr diff "$PR" --repo "$REPO" > "$DIFF_FILE"
gh pr view "$PR" --repo "$REPO" --json title,body,headRefName \
  --template $'TITLE: {{.title}}\nBRANCH: {{.headRefName}}\n\n{{.body}}' > "$META_FILE"

# Check out the PR head into a throwaway worktree so we never disturb REPO_DIR's
# working tree or current branch.
echo ">> preparing worktree at PR head" >&2
git -C "$REPO_DIR" fetch -q origin "pull/$PR/head"
HEAD_SHA="$(git -C "$REPO_DIR" rev-parse FETCH_HEAD)"
git -C "$REPO_DIR" worktree add -q --detach "$WT" "$HEAD_SHA"

# Build the orchestrator prompt with paths substituted in.
PROMPT="$(DIFF_FILE="$DIFF_FILE" META_FILE="$META_FILE" ENG_DIR="$ENG_DIR" \
  ORG_PROFILE="$ORG_PROFILE" PR_REVIEW_LANG="$PR_REVIEW_LANG" \
  envsubst '$DIFF_FILE $META_FILE $ENG_DIR $ORG_PROFILE $PR_REVIEW_LANG' \
  < "$(dirname "$0")/orchestrator.md")"

echo ">> running review (model: $MODEL)" >&2
( cd "$WT" && claude -p "$PROMPT" --model "$MODEL" \
    --add-dir "$ENG_DIR" --add-dir "$WORK" ) > "$OUT_FILE"

# Parse the verdict.
CLASS="$(grep -m1 '^CLASSIFICATION:' "$OUT_FILE" | awk '{print $2}')"
TRIGGERS="$(grep -m1 '^TRIGGERS:' "$OUT_FILE" | sed 's/^TRIGGERS:[[:space:]]*//')"
# Fail-closed: if we could not parse a clear SAFE, treat as needing a human.
[ "$CLASS" = "SAFE" ] || CLASS="NEEDS_HUMAN"

# Human-facing body: drop the model's preamble and the ARCH_REVIEW_REQUIRED
# hand-off marker (everything up to and including it), start at the first
# report section, and trim trailing blanks / rules / orphan code-fences.
BODY="$(awk '/^=== VERDICT ===/{exit} seen{print} /ARCH_REVIEW_REQUIRED/{seen=1}' "$OUT_FILE")"
[ -n "$BODY" ] || BODY="$(sed '/^=== VERDICT ===/,$d' "$OUT_FILE")"   # fallback: marker omitted
BODY="$(printf '%s\n' "$BODY" | awk 'p||/^## /{p=1} p')"                # start at first "## " section
BODY="$(printf '%s\n' "$BODY" | awk '{a[n++]=$0} END{e=n-1; while(e>=0 && (a[e]~/^[[:space:]]*$/||a[e]=="```"||a[e]=="---")) e--; for(i=0;i<=e;i++) print a[i]}')"

if [ "$CLASS" = "SAFE" ]; then
  HEADER="$C_SAFE"
else
  HEADER="$C_NEEDS"
  [ -n "${TRIGGERS:-}" ] && [ "$TRIGGERS" != "none" ] && HEADER+=$'\n'"$C_REASONS $TRIGGERS"
fi

COMMENT="$(cat <<EOF
$C_TITLE

$HEADER

<details><summary>$C_SUMMARY</summary>

$BODY

</details>

---
$C_FOOTER
EOF
)"

if [ "$POST" = "--post" ]; then
  echo ">> posting comment on $REPO#$PR" >&2
  printf '%s' "$COMMENT" | gh pr comment "$PR" --repo "$REPO" --body-file -
  echo ">> posted." >&2
else
  printf '%s\n' "$COMMENT"
  echo "== verdict: $CLASS ($TRIGGERS) ==" >&2
fi
