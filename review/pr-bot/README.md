# PR pre-review bot

Runs the eng-standards reviewer + architecture pass on a GitHub PR, classifies it
**SAFE** vs **NEEDS_HUMAN** (fail-closed), and posts the result as a PR comment. The
goal is to take the reviewer out of the loop on the safe majority of PRs: the bot
green-lights low-risk changes so they can merge without a second human pass, and
escalates anything risky.

## Usage

```sh
# dry-run: print the comment it would post
review/pr-bot/run.sh empresa-digital/empresa-digital 557

# post the comment on the PR
review/pr-bot/run.sh empresa-digital/empresa-digital 557 --post
```

## Auth — plan token, not the metered API

Set `CLAUDE_CODE_OAUTH_TOKEN` to a Claude Code **plan** OAuth token (generate with
`claude setup-token`). Runs then bill against the plan, not the Anthropic API. The
script also falls back to `CODECOMPANION_OAUTH_TOKEN` if that is exported.

## What it does

1. Fetches the PR diff + metadata via `gh`.
2. Checks the PR head into a throwaway `git worktree` (never disturbs your working
   tree or current branch).
3. Runs `review/reviewer.md` then `review/architecture-reviewer.md` as a single
   top-level orchestration (`review/pr-bot/orchestrator.md`), against the full repo.
4. Parses a machine verdict and posts a Portuguese comment: a SAFE line
   (`PR considerado seguro pra merge sem revisão extra`) or a `Requer revisão humana`
   line with the triggers, plus the full review folded in a `<details>` block.

## Classification (fail-closed)

`NEEDS_HUMAN` if **any** hold — and whenever the reviewer is unsure:

- any Blocker-severity finding
- complex or potentially slow code (real performance risk)
- a breaking API change affecting services outside this monorepo
- a DB schema change or migration
- a change to critical infrastructure (k8s, CI/CD, secrets, deploy/GitOps)

## Env overrides

| var | default | meaning |
|---|---|---|
| `ENG_DIR` | `~/.cache/eng-standards` | rule library root |
| `REPO_DIR` | `~/projects/<repo-basename>` | local checkout to review from |
| `ORG_PROFILE` | `empresa-digital.yaml` | org profile under `orgs/` |
| `MODEL` | `sonnet` | model for the review pass |

## Status

**Phase 1 — experimental.** The bot only comments; it does **not** merge or approve.
Otávio self-merges PRs it marks SAFE. Phase 2 (bot auto-approves SAFE on the team's
behalf) waits until its SAFE calls are shown to match human judgment. A natural home
for the trigger is a GitHub Actions `pull_request` workflow; today it runs on demand /
from a local cron.
