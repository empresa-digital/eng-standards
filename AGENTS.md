# AGENTS.md — eng-standards

This repo is a rule library, not an application. Agents consume it; they don't run it.

## How to use these rules

When reviewing or writing code, load rules **selectively by the file types touched**,
to keep context small:

- `.go` files → `universal.yaml` + `packs/backend-go.yaml` + `packs/testing.yaml`
  + the active org profile
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
