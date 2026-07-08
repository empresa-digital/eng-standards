---
name: "go-arch-lint-setup"
description: "Configure per-module go-arch-lint from a Go repo's documented hexagonal architecture; gates on a clear description, proposes config before writing."
---

# go-arch-lint-setup

Configure **`go-arch-lint`** to mechanically enforce a Go module's documented
hexagonal import boundaries. This is the tool half of the eng-standards rule
`go-arch-import-boundary-enforced`; the semantic half stays with the architecture reviewer.

## When to use

- A Go backend module documents a layered/hexagonal architecture but has no
  import-boundary linter, or its `.go-arch-lint.yml` is missing/partial.
- The architecture reviewer emitted `[go-arch-import-boundary-enforced]`.

Do **not** use this to invent an architecture. It enforces one that already exists.

## Hard gate — a clear architecture description is required

The config is derived from the repo's own description, never guessed.

1. Pick **one Go module** (one `go.mod`). A monorepo has several; handle one per run.
   If ambiguous, ask which module.
2. Find the architecture description in `AGENTS.md`, `CLAUDE.md`, or `README.md`. It
   must name the **roles** (core, core services, ports, outbound adapters, inbound
   adapters, helpers) and **who may import whom**. The canonical shape of such a
   description is `references/hexagonal-go.md` in eng-standards.
3. **If the description is missing or too vague to derive boundaries: STOP.** Tell the
   user the architecture isn't documented precisely enough and do not write any config.
   Only if the user **explicitly asks you to proceed anyway** may you extrapolate:
   draft a precise "Architecture" section (roles + an import matrix of who-may-import-whom)
   into `AGENTS.md`/`CLAUDE.md`, present it for **human review**, and STOP. After the
   human approves, run this skill again against the now-clear description.

## Procedure

### 1. Install the tool (if missing)
Match the repo's existing tool-install pattern (these repos `go install` pinned tools in
the Makefile `setup` target alongside staticcheck/richgo):
```
go install github.com/fe3dback/go-arch-lint@latest
```
Add it to the module's `setup`/`$(GOBIN)` target so CI installs it too. Do **not**
introduce golangci-lint.

### 2. Map roles to packages — then confirm before writing
Scan the module's folders and infer a role→path mapping. **Present the proposed mapping
to the human and get confirmation before writing any config.** If a package's role is
ambiguous, ask — do not assume.

**Key insight (validated on a real module):** go-arch-lint matches **packages by
directory depth**, not by filename. In the default layout the port packages (`contracts.go`)
sit **one level** under `adapters/` and the implementations **one level deeper**, so
`ports: adapters/*` and `outbound: adapters/*/*` are disjoint and need no precedence rules.
Do not try to match ports by filename (`adapters/**/contracts.go`) — match the package dir.

### 3. Generate `.go-arch-lint.yml` (version 3) at the module root
Translate the import matrix into components + deps. Validated skeleton (adapt component
names/globs to the confirmed mapping):
```yaml
version: 3
allow:
  depOnAnyVendor: false
  deepScan: false   # REQUIRED off. deepScan's DI-graph mode attributes an injected
                    # dependency to the constructor's component instead of the call site,
                    # so it false-positives on dependency injection (our normal pattern).
                    # We enforce import boundaries only.
components:
  core:     { in: core }
  services: { in: core/* }
  ports:    { in: adapters/* }     # the contracts.go packages
  outbound: { in: adapters/*/* }   # the implementations, one level deeper
  cmd:      { in: cmd/** }
  helpers:  { in: helpers/** }
deps:
  core:     { mayDependOn: [helpers] }
  services: { mayDependOn: [core, ports, helpers] }
  ports:    { mayDependOn: [core, helpers] }
  outbound: { mayDependOn: [core, ports, helpers], anyVendorDeps: true } # adapts external tech
  cmd:      { anyProjectDeps: true, anyVendorDeps: true }                 # entrypoint: imports anything
  helpers:  { mayDependOn: [helpers] }
```
Rules for the mapping:
- **outbound → `anyVendorDeps: true`** is required: it lets the adapter import the external
  technology it adapts (db driver, HTTP client, SDK) without false positives.
- **inbound (`cmd`) → `anyProjectDeps: true` + `anyVendorDeps: true`**, not an enumerated
  `mayDependOn` list — an entrypoint may import anything, including sibling `cmd/*` packages
  (middlewares, assets) and embedded resources (e.g. a `migrations` package).
- **helpers**: keep them tight; if a specific test lib (e.g. `testify`) must be allowed,
  model it as a named `vendors:` block and grant it via `canUse:` rather than a blanket
  `anyVendorDeps`.
- **Do NOT exclude `_test.go`** — tests follow their package's role.
- Map any unattached package (e.g. an embedded-SQL `migrations` package imported only by
  `cmd/*`) to the inbound component so the scanner doesn't report it as unmapped.

### 4. Run the check
```
go-arch-lint check --project-path <module-root>
```
Exit 0 = clean, 1 = violations. **Report existing violations; do not auto-fix production
code.** If a "violation" is actually a mislabeled package, fix the *mapping* with the
human — never loosen a real boundary to make the check pass.

Gotcha: go-arch-lint's scanner uses `filepath.Walk` and can panic on an unreadable dir
(e.g. a root-owned local docker volume like `.data`) *before* `exclude` applies. Add such
dirs to `exclude:` regardless; if it still blocks a local run, validate against a copy
without that dir. CI is unaffected (the dir won't exist there).

### 5. Wire into lint + CI
Add `go-arch-lint check` to the module's `make lint` target (next to staticcheck/go vet).
**Confirm CI actually runs it** — if CI runs staticcheck/vet directly instead of `make lint`,
add a `go-arch-lint check` step (installing the binary first) to the CI job, otherwise the
linter is configured but never enforced.

### 6. Report
Config path, the confirmed role→path mapping, install/CI changes, and the check result
(clean or the list of violations found).

## References
- `references/hexagonal-go.md` — the architecture model this enforces.
- Rules: `u-architecture-description-present`, `go-arch-import-boundary-enforced`, `go-hex-*`.
- go-arch-lint v3 config syntax: https://github.com/fe3dback/go-arch-lint (`vendors`,
  `commonComponents`, `mayDependOn`, `canUse`, `anyVendorDeps`, `anyProjectDeps`).
