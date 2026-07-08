# AGENTS.md — eng-standards

This repo is a rule library, not an application. Agents consume it; they don't run it.

## How to use these rules

When reviewing or writing code, load rules **selectively by the file types touched**,
to keep context small:

- `.go` files → `universal.yaml` + `packs/backend-go.yaml` + `packs/testing.yaml`
  + the active org profile
- `.go` files in a repo with a documented architecture → additionally run
  `review/architecture-reviewer.md` (on a strong model) as its own review pass; it loads
  `packs/architecture-hexagonal-go.yaml` + `references/hexagonal-go.md` itself
- `.ts` / `.tsx` files → `universal.yaml` + `packs/backend-ts.yaml` + `packs/testing.yaml`
  + the active org profile
- `.vue` / `.js` files → `universal.yaml` + `packs/frontend-vue.yaml` + `packs/testing.yaml`
  + the active org profile
- SQL / migrations → `universal.yaml` + `packs/database.yaml` + active org profile
- always also load `packs/git.yaml` for commit/branch work and `packs/planning.yaml`
  when decomposing tasks

The **active org profile** is the company file for the repo under review (e.g.
`orgs/empresa-digital.yaml`). A consuming repo declares which org profile applies in
its own `AGENTS.md`. Outside that company, skip org profiles entirely — the universal
and language packs still apply.

## Skills

Agent skills that pair with these rules live in `skills/` (one directory per skill, e.g.
`skills/go-arch-lint-setup`). This repo's `make setup` symlinks each one into
`~/.claude/skills/`, so they install together with the rule library — no per-skill step.
Claude Code discovers skills at **session start**: if a rule or reviewer points to a skill
you don't see, run `make setup` in `~/.cache/eng-standards` and use it in the next session.

## When flagging an issue

Cite the rule `id`. Prefer `severity: blocker` findings; surface `nit`s separately so
the author isn't flooded. If you diverge from a rule, say why (see
`u-document-divergent-decisions`).

## Editing rules

See `README.md` for the schema and the bucket sorting test. Every rule needs a stable
`id`, a `bucket`-appropriate home, and `sources`. Changes flow through a reviewed PR
(never auto-merged); CI validates the schema.

## The `lintable` flag

A rule marked `lintable: true` is mechanically checkable (deterministic, no judgment).
We intend to build our own linter and progressively offload these rules to it — a
linter enforces them deterministically without spending agent tokens or risking AI
drift. Until that exists, treat `lintable: true` rules the same as any other when
reviewing. `lintable: false` rules need human/agent judgment and will always live here.
