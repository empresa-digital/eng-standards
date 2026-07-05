# How we do Hexagonal Architecture in Go

The shared mental model for reviewing (and building) our Go services. This is
**reference prose**, not a rule pack — it defines the architecture so an LLM reviewer,
a human, or a lint-config generator can decide which package plays which role and what
each role is allowed to import. The `packs/backend-go.yaml` rules enforce individual
facets of what is described here; this doc is the picture they add up to.

The architecture is defined **by role**, not by folder path. A repo identifies which
package is which; folders are free to change over time. Verik is our **default layout** —
the reference we reach for when starting a new project or when in doubt — so its paths
appear throughout as a **labeled example**, never as a mandate.

## The roles

### Core (domain)

Pure domain logic. Pure functions, domain entities, domain error types, validators. No
side effects, no I/O, no awareness of how the app is delivered or executed.

- **May import:** the stdlib and helper packages — nothing else.
- **Must not import:** ports, adapters, entrypoints, or any external dependency.
- *Verik example:* `core/*.go`.

### Core services

Application services that orchestrate domain logic to fulfill a use case. Each is a
public `Service` struct with methods; adapters are injected (as port interfaces) at
construction.

- **May import:** stdlib, the core package, port packages, helpers.
- **Must not import:** adapters (implementations), entrypoints, or external
  technology libraries directly.
- **Calling another service:** a service may depend on another core service **only through
  a core-declared interface**, never by importing the sibling service package directly.
  Direct service-to-service imports invite import cycles; an interface owned by core breaks
  them. (This is an application of "depend on ports, not implementations" *inside* core.)
- *Verik example:* subdirectories of `/core`.

### Ports

The interfaces a service depends on and that driven adapters implement. Usually declared
in `contracts.go` files. A DTO used only by a port interface lives **in the same file,
right next to that interface** — not in an adapter and not in a shared types package
(that invites import cycles or forces the method off the interface).

- **Role, not path.** A `contracts.go` file is the **ports** role even when it physically
  sits *under* an `adapters/` subtree (a common layout: the port lives next to the adapter
  that implements it). A core service importing that package is importing a **port**
  (allowed), not an adapter (forbidden) — judge by what the file declares (interfaces), not
  by the directory it happens to live in.
- *Verik example:* `contracts.go` alongside the service that owns the port, e.g.
  `adapters/crm/contracts.go`.

### Outbound adapters (driven / client adapters)

Implement a port by adapting **exactly one** external technology: a database, an object
store, a message broker, another service's HTTP API, an LLM API, and so on. They
translate external complexity — including foreign error types — into domain types and
domain errors before returning.

- **May import:** stdlib, the core package, port packages, helpers, **and the external
  dependencies relevant to the technology it adapts.**
- **Must not import:** another outbound adapter's **implementation** package, any inbound
  adapter, or anything that reflects *how the app is executed* (worker / server / lambda
  wiring).
- **Needing a sibling adapter (rare):** just like a core service, an outbound adapter may
  depend on a **port interface** injected via DI. If it genuinely needs another adapter, it
  goes through that sibling's port interface + dependency injection — never a direct import
  of the sibling's implementation package.
- *Verik example:* `/adapters/**`.

**Nuance — do not get this wrong.** There is **no blanket ban on technology in an
outbound adapter.** An outbound adapter is *supposed* to be coupled to the tech it
adapts: a Postgres client library belongs in a repository adapter; an HTTP client
belongs in an adapter that calls an external API; an S3 SDK belongs in a blob-store
adapter. Flagging "this adapter imports a database driver" is a false positive. The real
violations are: importing a *sibling* adapter's **implementation** (a sibling's port
interface via DI is fine), importing an *inbound* adapter, or pulling in execution/delivery
concerns.

### Inbound adapters (entrypoint / driving adapters)

HTTP controllers, message-broker workers, CLI entrypoints, and `main.go` with the DI
wiring. These are the outermost layer.

- **May import:** anything.
- Inbound adapters are **intentionally coupled directly to service implementations**, not
  to service interfaces. This is a deliberate Verik decision: importing the concrete
  service discourages ceremonial mock-interfaces at the entrypoint and keeps integration
  tests exercising the real service logic. Do not flag an entrypoint for depending on a
  concrete service.
- *Verik example:* `/cmd/*`.

### Helpers

Small utilities with no side effect anyone would want to mock (formatting, parsing, pure
conversions).

- **May import:** stdlib or other helpers — nothing else.
- `testify` is treated as an external helper package.
- A helper that reads **ambient config** (environment variables, flags) is **not** a pure
  helper — env-reading is inbound-only (see *Configuration & environment*). Judge such code by
  what it does (`os.Getenv`), not by the `helpers/` bucket it sits in.

### Test files

Test files obey the **same import rules as the role of the package they live in** — there
is no separate allowance for `_test.go`. What look like exceptions are really consequences
of this rule:

- Integration tests that need to wire several layers belong in **inbound adapters**, which
  may import anything. That is their normal home.
- An **outbound adapter's** tests may import a generic database or HTTP client library even
  when the adapter's production code happens not to — the outbound role already permits the
  technology it adapts and the libraries needed to talk to it, and the test is bound by that
  same role, not a looser one. It is not an exception; the coupling was always allowed there.

The rules are fixed; understanding these flexibility points is what makes them practical.

## Dependency direction at a glance

| Role | May import |
|---|---|
| Core (domain) | stdlib, helpers |
| Core services | stdlib, core, ports, helpers |
| Ports | stdlib, core, helpers (interfaces + their DTOs) |
| Outbound adapter | stdlib, core, ports, helpers, **+ the external tech it adapts** |
| Inbound adapter | anything (couples directly to concrete services) |
| Helpers | stdlib, other helpers |

Dependencies point **inward**: entrypoints → services → ports ← adapters, with core at
the center depending on nothing but the stdlib and helpers. **Sideways** moves are
forbidden within a layer too: an outbound adapter must not import a sibling adapter's
implementation, and a service must not import a sibling service — both reach a sibling only
through a **port/core interface injected via DI**, never a direct import. Two
things an import linter cannot see but a reviewer must: an adapter pulling in
execution/delivery concerns, and the semantic violation below.

## Semantic violation: domain types coupled to a delivery mechanism

This is a class of violation an import linter **cannot** catch, so the reviewer owns it.

**A core/domain type must not gain an attribute whose only reason to exist is a specific
transport or delivery mechanism.**

Canonical example — the domain error type. It carries a transport-agnostic
`Code string` (`NotFound`, `AlreadyExists`, `Internal`, …). It must **not** grow a
`Status int` field holding an HTTP status code just to make conversion easier in the HTTP
middleware. That field exists *only because HTTP exists*; it drags a delivery concern into
the domain. The `Code` → HTTP-status mapping belongs in the **inbound HTTP
adapter/middleware**, keyed off `Code`.

```go
// WRONG — Status only exists because HTTP exists.
type Error struct {
    Code    string
    Status  int    // HTTP status leaked into the domain
    Message string
}

// RIGHT — domain stays transport-agnostic; the HTTP adapter owns the mapping.
type Error struct {
    Code    string // NotFound | AlreadyExists | Internal | ...
    Message string
}
```

Clarifications that keep this from misfiring:

- Domain error **names** coinciding with HTTP concepts (`NotFound`, `Internal`) are fine
  and expected. The smell is coupling a domain *type* to a delivery *detail*, not the
  vocabulary.
- Some domain codes (`AlreadyExists`) have **no** HTTP equivalent, which underscores that
  the domain vocabulary is independent of HTTP — it is not a renamed status-code enum.

## Configuration & environment

An **environment variable is an artifact of the deploy environment**, not of the domain. The
responsibility to read env vars and translate them into config lives **only in the inbound
adapter** (the composition root / entrypoint). Every other layer — core, core services,
ports, outbound adapters, helpers — receives that config as **injected parameters** and must
never read the environment itself.

This is the same "don't assume how you're driven" rule applied to config: an outbound adapter
that reads `PIPEDRIVE_TOKEN` from the environment wouldn't work when driven by an Android or
desktop entrypoint that has no such env var. A strong tell is **asymmetry** — one value handed
in as a constructor parameter while another is read from the environment in the same
constructor. Reading env inside an inner layer is a common but wrong shortcut; the fix is
always to read it at the entrypoint and inject the value.

```go
// WRONG — outbound adapter reaches into the deploy environment.
func New(token string) *Client {
    return &Client{token: token, pipelineID: env.GetInt("PIPEDRIVE_PIPELINE_ID")}
}

// RIGHT — the inbound entrypoint reads env and injects; the adapter just receives.
func New(token string, pipelineID int) *Client {
    return &Client{token: token, pipelineID: pipelineID}
}
```

## Where a new type belongs

- **A new domain concept** → core.
- **A DTO for an external API** (request/response shapes when calling or being called by
  another system) → declared **inline and private at the translation site**. Prefer an
  anonymous `var body struct{ ... }` or `map[string]any` right where you marshal/unmarshal.
  Avoid package-level DTO types for external APIs — they leak an external contract into
  your namespace and tempt reuse across call sites.
- **A DTO used by a port interface** → next to the interface, in the same `contracts.go`
  file (see *Ports*).

## Go-specific pattern: repository implementation

An idiomatic shape for repository adapters that keeps a method reusable inside a
transaction: write the real logic as a **public function that takes the DB handle (or
transaction) as an argument**, and let a thin method satisfy the port by calling it with
the adapter's own connection.

```go
// Public function — reusable with any handle, including a *sql.Tx.
func InsertUser(ctx context.Context, db DBHandle, u core.User) error {
    // ... build + execute the query, translate errors into domain errors ...
}

// Thin method — implements the port using the adapter's own connection.
func (r Repo) InsertUser(ctx context.Context, u core.User) error {
    return InsertUser(ctx, r.db, u)
}
```

The method satisfies the interface; the function lets the same insert run inside a larger
transaction without duplicating the query or the error translation.

## Using this doc

- **Reviewers:** for a diff, identify each changed package's role, then check its imports
  against the table above and check every new domain type against the delivery-coupling
  rule. The sideways-adapter and delivery-coupling checks are the two an import linter will
  miss — spend judgment there.
- **A lint-config generator:** map each module to a role, then emit allowed-import sets
  from the table. The role boundaries are mechanical; the delivery-coupling rule stays with
  the reviewer.
