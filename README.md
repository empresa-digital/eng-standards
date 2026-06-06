# eng-standards

Shared, model-agnostic code-review rule library. Encodes review judgment so AI agents
catch issues at planning, implementation, and review time — before a human does.

Full design rationale lives in the `ai-assistant` repo:
`plans/ai-code-quality-initiative.md`.

## Layout

```
universal.yaml          # principles that bind to nothing — travel anywhere
packs/                  # bind to a language/paradigm — travel to any Go/Vue shop
  backend-go.yaml
  frontend-vue.yaml     # (slice 2)
  database.yaml         # (slice 2)
  infra.yaml            # (slice 2)
  git.yaml              # (slice 2)
  testing.yaml          # (slice 2)
  planning.yaml         # (slice 2)
orgs/                   # bind to a tool OR a house convention — do NOT travel
  empresa-digital.yaml  # one file per company; swap at a new job
scripts/
  validate.py           # CI schema-check (slice 2)
```

## The sorting test

Every rule lands in exactly one bucket. Ask:
**"Would this rule still be true if I swapped the ORM / framework / test lib / company?"**

- Yes, always → `universal.yaml`
- Yes, for this language/paradigm → `packs/<lang>.yaml`
- No, it names a tool or a house convention → `orgs/<company>.yaml`

Often only a rule's *example* is stack-flavored while its *principle* is portable.
Keep the principle in the language pack with a genericized example; move to an org
profile only when the rule exists *solely* because of a tool.

## Rule schema (YAML)

```yaml
meta:
  pack: backend-go          # file identity
  description: ...
  language: en
rules:
  - id: go-no-passthrough   # stable, semantic, kebab-case, pack-prefixed
    topic: Architecture
    severity: blocker        # blocker | nit
    lintable: false          # true = candidate for promotion to a linter
    sources: [be-001]        # origin refs (friend's rule ids / agent-improvements case N)
    principle: One-line statement of the rule.   # optional if wrong/right is enough
    wrong:
      description: What the bad version does.
      code: |
        // verbatim code, no escaping needed
    right:
      description: What the good version does.
      code: |
        // ...
    reason: Why. The justification an agent cites when flagging.
    solution: Optional remediation guidance.
```

Notes:
- Code goes in block scalars (`|`) — verbatim, no `\n`/quote escaping.
- A rule may omit `wrong`/`right` and carry only `principle` + `reason` when no code
  pair adds value (common in `universal.yaml`).
- `id`s are stable: the eval (W9) asserts the review agent flags the matching `id`,
  and each `wrong`/`right` pair doubles as a test fixture.

## Consumption

Agents load **selectively** by the file types in a diff:
- `.go` change → `universal` + `packs/backend-go` + `packs/testing` + active org
- `.vue` change → `universal` + `packs/frontend-vue` + `packs/testing` + active org

The "active org" is the company profile for the current repo (configured in that
repo's `AGENTS.md`). This keeps context small and avoids the "long guidance file
ignored" failure mode.

## Setup (distribution)

Consumers don't vendor this repo. They pull the latest into a shared cache:

```sh
make setup   # clones to ~/.cache/eng-standards, or pulls if already present
```

Always latest, no submodule, no filesystem-path assumptions. Public repo → no auth.
