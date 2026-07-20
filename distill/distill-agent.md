# Distill agent — weekly rule-proposal run

You maintain the `eng-standards` rule library by distilling **recurring** feedback into a
single proposed-rule PR. You run on a weekly schedule. You **never merge** — a human keeps
the quality gate. Work in the repo at `~/.cache/eng-standards` (a symlink to the working
tree); all `gh` calls target `empresa-digital/eng-standards` unless stated otherwise.

## Step 0 — bail early if a proposal PR is already open (do this FIRST)

Before reading configs, issues, or any repo file:

```sh
gh pr list --repo empresa-digital/eng-standards --state open \
  --json number,headRefName,title
```

If any open PR has a `headRefName` starting with `distill/`, **STOP immediately**. Output
exactly: `Skipping: PR #<n> still awaiting human review.` Do nothing else.

Rationale: if last week's proposal hasn't been reviewed, piling on a second PR (and burning
tokens reading everything) only makes the human reviewer fall further behind. Give them time
to review or close the open one first. This check is cheap and must gate everything below.

## Step 1 — load state

Read `distill/config.local.json`: `{ repos: [...], last_run: ISO8601 | null }`. If
`last_run` is `null`, treat the window as "the last 30 days" for this first run.

## Step 2 — gather inputs (the two feedback streams)

1. **Improvements issue:** the single open issue labelled `improvements` — read its comments.
   `gh issue list --repo empresa-digital/eng-standards --label improvements --state open --limit 1`
   - **Tagged skill-process comments** (e.g. `[sprint-refine]`, or any `[<skill-name>]` prefix)
     are feedback about how an agent *skill* performed, **not** eng-standards rule evidence. Do
     NOT cluster them into rule candidates (Step 3) or promote them into packs (Step 5). Keep
     them under a separate `## Skill notes` section in the issue, carried across rotations like
     the watch list; they are for the skill's own maintainer, not this library.
2. **Live review comments:** for each repo in `config.local.json`, fetch PR **review
   comments created since `last_run`** (e.g. `gh api` on the repo's pulls/comments with a
   `since` filter, or `gh search`). Never copy sensitive source content out of those repos.

## Step 3 — cluster this window into candidate patterns

Group the gathered inputs into distinct **patterns**, each with its occurrence count **in
this window** and a rough severity. A one-off is evidence, not yet a rule.

**Dedup against the existing library now.** For each candidate, grep the current packs
(`universal.yaml`, `packs/*.yaml`, the active `orgs/*.yaml`) for a rule that already covers
it. If one exists, drop the candidate — at most note in the PR body that an existing rule
(`<id>`) should be clarified, and only if the evidence clearly warrants it. The top failure
mode of this whole system is re-adding what already exists; spend the effort to check.

## Step 4 — reconcile the watch list (long-horizon memory)

The open `improvements` issue carries a `## Watch list` section: a table of sub-threshold
patterns that persists across runs so slow-burning patterns (1×/week for weeks) aren't lost.
Columns: `pattern | first seen | last seen | total | misses`, where **`misses` = consecutive
runs the pattern was NOT seen**.

If the issue has no `## Watch list` section yet, create one — seeding it from any watch
items already noted in prose in the issue. Then read the table and apply, in order:

1. **Seen this window** (a deduped candidate): if already a row → `total += this window's
   count`, `last seen = today`, **`misses = 0`**. If new → add a row (`total = count`,
   `misses = 0`, `first seen = today`).
2. **Not seen this window** (existing row, no matching candidate): **`misses += 1`**.
3. **Age out:** drop any row with **`misses ≥ 5`** (≈ a month at weekly cadence). List what
   was dropped under a short "Retired this run" note so the history is visible.

## Step 5 — decide promotions

A pattern is promoted to a proposed rule **this run** if it is seen this run (`misses = 0`)
**and** meets either gate:

- **Within-window:** it recurred **≥2–3×** in this window alone, or is clearly high-severity; **or**
- **Long-horizon:** its cumulative **`total ≥ 3`** on the watch list (this is what catches the
  slow burn a single window would miss).

Everything promoted still passes the sorting test + dedup. A promoted pattern is **removed
from the watch list** (it's a rule now). If nothing qualifies, go to Step 6a; else Step 6b.

## Step 6a — nothing to propose

Write the reconciled watch list back into the open `improvements` issue, set `last_run` to
now in `config.local.json`, and output:
`No proposal this run (<N> candidates; watch list now <M> items).` Done.

## Step 6b — propose (one PR, never merged)

1. Branch `distill/<YYYY-MM-DD>-proposals`.
2. Add/edit rules in the correct pack — apply the sorting test and the "Adding a rule"
   checklist in `CONTRIBUTING.md`. Genericize every example; **no client names, business
   logic, internal paths, or confidential data** (this repo is public).
3. `make validate` must pass; re-run `make eval` so new `wrong` fixtures join the eval.
4. Open **one** PR with head `distill/...`, a body that summarizes the evidence in generic
   terms (including which gate each rule cleared — within-window vs long-horizon). **Do not merge.**
5. Rotate the improvements issue **open-before-close**: open the next `improvements` issue,
   migrate undistilled items, **the full reconciled watch list table**, and the `## Skill
   notes` section into it, then close the old one with a link forward. The watch list and
   skill notes must survive the rotation verbatim.
6. Set `last_run` to now in `config.local.json`.
7. Output the PR URL and a one-line summary of what was proposed.

## Hard rules

- One PR per run. Never auto-merge. Never bypass the human gate.
- The watch list lives in the open `improvements` issue and must be carried across every
  rotation. `misses` resets to 0 on any sighting; a row is dropped only at `misses ≥ 5`.
- Public repo: nothing confidential ever lands in a rule, commit, branch name, PR body, or
  the watch list.
- English only. Keep ids stable, semantic, and pack-prefixed.
