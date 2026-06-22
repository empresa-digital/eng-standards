# Contributing & Maintenance

Design rationale and the rules of thumb that keep this library trustworthy as it grows.
For the rule **schema** and **consumption** (which files exist, how agents load them), see
the README; this doc covers the *why* and the maintenance discipline.

## Philosophy

Encode review judgment as concrete, model-agnostic rules so AI agents catch issues at
**planning, implementation, and review** time — before a human does. Plain YAML, English,
no vendor coupling, so the library travels to any shop.

The rule set is **finite, not infinite.** Independent sources of review feedback converge
heavily (roughly 60%) onto the same recurring mistakes — a deduped set of low hundreds,
not thousands. The job is to find that set, not to log every incident.

## The sorting test

Every rule lands in exactly one bucket. Ask:
**"Would this rule still be true if I swapped the ORM / framework / test lib / company?"**

- Yes, always → `universal.yaml`
- Yes, for this language/paradigm → `packs/<lang>.yaml`
- No, it names a tool or a house convention → `orgs/<company>.yaml`

Often only a rule's *example* is stack-flavored while its *principle* is portable. Keep the
principle in the language pack with a genericized example; move to an org profile only when
the rule exists *solely* because of a tool or house convention.

## Distill, don't transcribe

A new rule comes from a recurring *pattern*, not from a single incident.

- **Domain-specific cases inform a principle; they don't become rules.** "This payment
  event must stay immutable" is evidence for a universal principle (e.g. one source of
  truth, no invalid-state code) — the principle is the rule, the case is not.
- **Genericize the principle; specialize only when tool-bound.** Often only a rule's
  *example* is stack-flavored while its *principle* is portable. Keep the principle in a
  language pack with a genericized example. Move it to an org profile **only when the rule
  exists solely because of a tool or a house convention** — apply the sorting test (would
  it still be true after swapping the ORM / framework / test lib / company?).
- Tool-bound or opinionated rules that land in a language pack or `universal` will
  **mislead at a different shop** — that is the failure the org-profile split prevents.

## Severity discipline

Tag every rule `blocker` or `nit`. The reviewer ranks by severity so a reader isn't
drowned in nits; an unranked wall of minor findings gets ignored, taking the blockers
with it. Reserve `blocker` for correctness/architecture; style and taste are `nit`.

## `lintable` and promotion to a linter

`lintable: true` marks a mechanically checkable rule (deterministic, no judgment).
We will eventually write our own linter to move these rules to a deterministic checker
instead of spending tokens or risking model drift on every review. Promote a
rule out of the agent's context and into a linter **only when it is high-frequency and
low false-positive** — most of the library needs judgment and stays with the agent.

## The rules ARE the eval

Each `wrong`/`right` pair doubles as a test fixture:

- Feed the `wrong` code to the reviewer and assert it flags that rule's `id`.
- **Bracket-only contract:** a bracketed `[rule-id]` in reviewer output means *violated* —
  only on a finding line, never to clear a rule. This is what makes the eval
  machine-checkable.
- **Always run the negative control first.** Feed the `right` code and assert the rule is
  *not* flagged. A naive "is the id mentioned?" match scores deceptively high because the
  reviewer cites ids in prose to *clear* them — a perfect-looking catch-rate with near-zero
  specificity. Never trust a catch-rate until the negative control passes.
- Snippet-based eval understates rules that need repo-wide context (reuse,
  one-source-of-truth); tag those so the score is read honestly.

## id stability

`id`s are stable, semantic, kebab-case, and pack-prefixed. The eval and any downstream
references depend on them — never rename or reuse an `id`. Retire a rule by removing it,
not by repurposing its `id`.

## Selective loading

Agents load only the packs relevant to a change (by file type and workflow stage). This
controls token cost and avoids the "long guidance file silently ignored" failure mode.
Keep packs small and orthogonal so a consumer pays only for what a given diff touches.

## Feedback loop — how the library grows

Rules are added by a scheduled maintenance agent that reads through PRs and reported usage
issues (as comments on a GH issue) and creates a PR with proposed changes.

Its two inputs:

- **Reported usage issues** — a single **open issue** labelled `improvements`, where agents
  append **comments** (the platform serializes them, so concurrent writers never conflict).
- **Live review comments** from the repos of interest, fetched with a time-windowed query
  at run time. Never copy sensitive source into this repo; everything committed here stays
  generic — no client names, business logic, or confidential data.

Its operating rules:

- **Skip the run if a proposal PR is still open.** Before reading anything else, check for an
  open distill PR; if one exists, stop — don't review, don't open a second PR. Let the human
  catch up on the pending one first, or proposals pile up and the reviewer tunes them out.
  (This check goes first precisely so a backed-up queue costs almost no tokens.)
- **Gate on recurrence.** Propose a rule only when the same pattern shows up ≥2–3× or is
  high-severity. A one-off is evidence, not yet a rule — **"no new rule this run" is a
  valid, expected outcome.**
- **One PR per run, never auto-merged.** Batch every proposal into a single PR; a human
  reviews it and keeps the quality gate.
- **Rotate the issue open-before-close.** Open the next `improvements` issue, move any
  undistilled items over, then close the old one with a link forward — so a concurrent
  agent always finds exactly one open issue.
- **Promote** mechanical, high-frequency rules to the linter backlog.

## Adding a rule — checklist

1. It's a recurring pattern, not a one-off incident.
2. Sorting test passed → it's in the right bucket (`universal` / language pack / org).
3. Principle is generic; any tool-specific flavor lives in an org profile.
4. `severity` and `lintable` set honestly.
5. A `wrong`/`right` pair (or `principle` + `reason` when no code pair adds value).
6. `id` is new, semantic, and pack-prefixed.
7. `make validate` passes; re-run `make eval` (the new fixture joins it automatically).
