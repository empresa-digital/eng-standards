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

## Auth

- **Locally:** nothing to set — the script uses your existing `claude` login.
- **In CI:** export `CLAUDE_CODE_OAUTH_TOKEN` with a Claude Code **plan** OAuth token
  (generate with `claude setup-token`) so runs bill against the plan, not the metered
  Anthropic API.

> Don't export `CLAUDE_CODE_OAUTH_TOKEN` globally on a dev machine (e.g. in `.bashrc`):
> the CLI reads it and it can shadow your interactive login, breaking things like
> `/usage`. Set it only in the CI job's environment.

## CI / GitHub Actions

`github-actions.example.yml` is a ready-to-copy `pull_request` workflow. Copy it into
the target repo as `.github/workflows/eng-standards-pre-review.yml`, set `<ORG>` to the
eng-standards owner, and add two secrets:

- `CLAUDE_CODE_OAUTH_TOKEN` — a plan OAuth token (`claude setup-token`), so runs bill
  against the plan, not the API.
- `ENG_STANDARDS_TOKEN` — a read PAT for the private eng-standards repo (drop it, and the
  `token:` line, if eng-standards is public).

The job checks out both repos, installs the toolchain (`envsubst`, `pyyaml`, `claude`),
and runs `run.sh … --post`. It only comments — never merges or approves.

## What it does

1. Fetches the PR diff + metadata via `gh`.
2. Checks the PR head into a throwaway `git worktree` (never disturbs your working
   tree or current branch).
3. Runs `review/reviewer.md` then `review/architecture-reviewer.md` as a single
   top-level orchestration (`review/pr-bot/orchestrator.md`), against the full repo.
4. Parses a machine verdict and posts a comment: a SAFE line or a "human review
   required" line with the triggers, plus the full review folded in a `<details>`
   block. The comment's language and its fixed strings come from the org profile's
   `meta.pr_review` block (see [Language](#language)), so the tool itself is
   language-neutral.

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
| `MODEL` | `opus` | model for the review pass |

## Language

The bot has no language of its own. The review prose and the fixed comment strings
(title, headers, footer) come from the active org profile's `meta.pr_review` block:

```yaml
meta:
  pr_review:
    language: pt-BR
    comment:
      title: "..."
      details_summary: "..."
      safe_header: "..."
      needs_human_header: "..."
      reasons_label: "..."
      footer: "..."
```

If a profile omits that block, the bot falls back to generic English. To localize the
bot for another org, edit that org's profile — not this tool. (Reading it needs
`python3` + `pyyaml`, which the repo already uses for `scripts/validate.py`.)

## Status

**Phase 1 — experimental.** The bot only comments; it does **not** merge or approve.
The PR author self-merges changes it marks SAFE. Phase 2 (bot auto-approves SAFE on the
team's behalf) waits until its SAFE calls are shown to match human judgment. The
GitHub Actions `pull_request` trigger is drafted in `github-actions.example.yml` (see
[CI](#ci--github-actions)); until it's installed, the bot runs on demand / from a
local cron.
