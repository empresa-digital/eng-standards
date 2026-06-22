# eng-standards

Shared, model-agnostic code-review rule library. Encodes review judgment so AI agents
catch issues at planning, implementation, and review time — before a human does.

Any rule additions or changes in general in this repo should be made after considering
the [`CONTRIBUTING.md`](CONTRIBUTING.md) file where the design rationale and maintenance
discipline lives.

## Layout

```
universal.yaml          # principles that bind to nothing — travel anywhere
packs/                  # bind to a language/paradigm — travel to any Go/Vue shop
  backend-go.yaml
  backend-ts.yaml
  frontend-vue.yaml     # (slice 2)
  database.yaml         # (slice 2)
  infra.yaml            # (slice 2)
  git.yaml              # (slice 2)
  pull_requests.yaml    # PR description / title / scope conventions
  testing.yaml          # (slice 2)
  planning.yaml         # (slice 2)
orgs/                   # bind to a tool OR a house convention — do NOT travel
  empresa-digital.yaml  # one file per company; swap at a new job
review/
  reviewer.md           # adversarial reviewer prompt
scripts/
  validate.py           # CI schema-check
  eval.py               # eval: does the reviewer catch our own rules?
```

For **which bucket** a rule belongs in (the sorting test) and the rest of the maintenance
rationale, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

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
    lintable: false          # true = mechanically checkable; offload target for our linter
    sources: [be-001]        # origin refs (source rule ids / logged review cases)
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
- `id`s are stable: the eval asserts the review agent flags the matching `id`,
  and each `wrong`/`right` pair doubles as a test fixture (see `CONTRIBUTING.md`).

## Using this library

Agents should use these rules whenever required by a user, AGENTS.md or equivalent
and here's how to use this library:

Agents load rules **selectively** by the file types in a diff:
- `.go` change → `universal` + `packs/backend-go` + `packs/testing` + active org
- `.ts` / `.tsx` change → `universal` + `packs/backend-ts` + `packs/testing` + active org
- `.vue` change → `universal` + `packs/frontend-vue` + `packs/testing` + active org

Some packs bind to a **workflow stage**, not a file type, so they load by review
context rather than by extension:
- planning a change → `packs/planning`
- writing commits / opening a PR → `packs/git` + `packs/pull_requests`
- infra/IaC changes → `packs/infra`

The "active org" is the company profile for the current repo (configured in that
repo's `AGENTS.md`). This keeps context small and avoids the "long guidance file
ignored" failure mode.

### Reviews

Whenever a task is completed using this standards the agent must start the reviewer sub
agent to check the newly made changes are matching the eng-standards.

If any parts of the code that were changed have dense business logic the reviewer agent
should be started again using a strong model (like Opus) and instructed to validate that
particular section of the code.
At the end report if he believes this code section is a good candidate to a high level
refactor focused review looking holistically for opportunities to shrink and simplify
that code. This review should also consider high level refactors including model changes
and changes in the overall project structure to address issues that might be making this
code more complex than necessary.

### Reporting issues & improvements

At the **end of a task** that used these standards, the consuming agent reports back so the
library can improve. Append a **comment** to the single open `improvements` issue in this
repo (find it with `gh issue list --label improvements --state open --limit 1`) covering:

- rough edges hit while applying a rule (unclear wording, false positive, missing case);
- a rule that should exist (a mistake the standards didn't catch) or one that misfired;
- any reviewer/tooling friction worth fixing.

Keep it **generic** — this repo is public, so never include client names, business logic,
internal paths, or confidential data. A scheduled maintenance agent distills these comments
into proposed rule PRs (see [`CONTRIBUTING.md`](CONTRIBUTING.md)); "nothing to report" is a
fine outcome.

### Setup (distribution)

Consumers don't vendor this repo. They pull the latest into a shared cache:

```sh
make setup   # clones to ~/.cache/eng-standards, or pulls if already present
```

Always latest, no submodule, no filesystem-path assumptions. Public repo → no auth.

Before starting any new task you run `make setup` just to make sure you are using
the latest version of the library.

## Review & eval

`review/reviewer.md` is the adversarial reviewer prompt. It loads the packs that match
the changed file types, explores the repo (the top failure — "does this already
exist?" — is invisible from a diff), and emits findings keyed to rule `id`s plus three
mandatory pushback sections (design risks / decisions unsure / cheaper alternatives).
Wire it into a consuming repo via that repo's `AGENTS.md` or a Claude subagent; the
prompt is plain text, so swapping agents means rewriting only the wrapper.

The library's own `wrong` fixtures double as the eval (see [`CONTRIBUTING.md`](CONTRIBUTING.md)
for why, the bracket-only contract, and the negative-control caveat):

```sh
make eval                      # all fixtures (needs the `claude` CLI)
make eval ARGS="--limit 5"     # cheap smoke run
make eval ARGS="--ids go-no-stuttering,go-json-camelcase"
```

By default the eval shows the reviewer **only the bad code**; pass `--with-desc` to add
the diagnosis back (an easier run). Rules needing repo-wide context are tagged
`repo-context`, since the snippet-only eval understates them.

### The `lintable` flag

`lintable: true` marks a rule that can be checked mechanically (deterministic, no
judgment call). We plan to write our own linter and migrate these rules to it over
time. Anything a linter can enforce shouldn't spend agent tokens or risk AI drift — so
moving a rule out of the agent's context and into the linter both cuts cost and makes
enforcement deterministic. `lintable: false` rules require judgment and stay with the
agent.
