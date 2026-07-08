# How we do Hexagonal Architecture in Go

The shared mental model for reviewing (and building) our Go services. This is
**reference prose**, not a rule pack — it defines the architecture so an LLM reviewer,
a human, or a lint-config generator can decide which package plays which role and what
each role is allowed to import. The `packs/architecture-hexagonal-go.yaml` rules are the
primary enforcement of what is described here (with `packs/backend-go.yaml` covering
adjacent Go conventions); this doc is the picture they add up to.

The architecture is defined **by role**, not by folder path. A repo identifies which
package is which; folders are free to change over time. Our **default layout** — the
reference we reach for when starting a new project or when in doubt — supplies the paths
that appear throughout as **labeled examples**, never as a mandate.

## The roles

### Core (domain)

Pure domain logic. Pure functions, domain entities, domain error types, and validators
for domain types/concepts (validation can also happen in other layers). No side effects,
no I/O, no awareness of how the app is delivered or executed.

- **May import:** the stdlib and helper packages — nothing else.
- **Must not import:** ports, adapters, entrypoints, or any external dependency.
- *Default layout:* `core/*.go`.

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
- *Default layout:* subdirectories of `/core`.

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
- *Default layout:* `contracts.go` alongside the service that owns the port, e.g.
  `adapters/crm/contracts.go`.

### Mocks

Any package that declares an interface should also declare a `mocks.go` **in that same
package**, built with the project's generic mock structure. Tests then mock the interface
from a ready-made mock instead of re-implementing the same boilerplate at every call site.

### Outbound adapters (driven / client adapters)

Implement a port to reach an external technology: a database, an object store, a message
broker, another service's HTTP API, an LLM API, and so on. An outbound adapter is
**self-contained, hides external complexity from the domain, and fulfills domain needs by
implementing port interfaces**. It translates external complexity — including foreign
error types — into domain types and domain errors before returning. (We do not enforce
single-responsibility at the architecture level; one adapter may lean on more than one
external piece — e.g. a NATS adapter that also uses JetStream.)

- **May import:** stdlib, the core package, port packages, helpers, **and the external
  dependencies relevant to the technology it adapts.** Importing the adapted technology's
  client library — and any other external libs genuinely needed to talk to it — is
  expected, not a smell.
- **Must not import:** another outbound adapter's **implementation** package, any inbound
  adapter, **core services**, or anything that reflects *how the app is executed* (worker /
  server / lambda wiring).
- **Needing a sibling adapter (rare):** just like a core service, an outbound adapter may
  depend on a **port interface** injected via DI. If it genuinely needs another adapter, it
  goes through that sibling's port interface + dependency injection — never a direct import
  of the sibling's implementation package.
- *Default layout:* `/adapters/**`.

### Inbound adapters (entrypoint / driving adapters)

HTTP servers, message-broker workers, CLI entrypoints, lambda function entrypoints, and
any `main.go` with the DI wiring. These are the outermost layer.

- **May import:** anything.
- Inbound adapters are **intentionally coupled directly to service implementations**, not
  to service interfaces. This is a deliberate decision: importing the concrete service
  discourages ceremonial mock-interfaces at the entrypoint and keeps integration tests
  exercising the real service logic. Do not flag an entrypoint for depending on a concrete
  service.
- *Default layout:* `/cmd/*`.

### Helpers

A **helper is a package with no side-effect anyone would ever want to mock, and not
coupled to anything specific to this domain** (formatting, parsing, pure conversions, and
the like). A helper *may* have generic dependencies — what matters is that the parts we
actually use have no side-effects we might want to mock and no domain coupling.

Example of a valid helper: a generic env-var parser (stdlib-only, no significant logic, no
hard-coded variable names, used only at startup). Nobody would ever want to mock it as it is
only to be used on the main function, and it knows nothing about this domain — so it qualifies,
even though it touches the environment.

- **May import:** stdlib or other helpers — plus generic external libraries whose used
  surface still has no side-effects we might want to mock and no domain coupling.
- `testify` is treated as an external helper package (the parts we use fit the definition).
- Judge a helper by what the parts we use actually *do*, not by the `helpers/` bucket it
  sits in: a package that performs domain-coupled I/O anyone would want to mock is not a
  helper no matter where it lives.

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

## Fakers

To build test instances of an entity/struct in a succint manner, declare a **faker function
in a `fakers.go`** in the **same directory as the struct**. Three rules:

1. **Deterministic** — calling the faker twice yields the exact same instance. No random
   values, no `time.Now()`; calling a faker function should have no surprising behavior
   so the test is easy to understand. Custom attributes must be passed explicitly.
2. **Dumb** — mandatory *identifying* args (unique keys, IDs, required foreign keys) are
   **positional**; everything unimportant is passed through a trailing `map[string]any{}`
   of overrides. Keep the signature small and the body obvious.
3. **Defaults allowed but discouraged** — prefer a dumb faker with no baked-in defaults;
   add a default only when its absence would force *most* tests to set that value every time.

```go
// fakers.go — same directory as User.
func FakeUser(id int, email string, overrides map[string]any) User {
    u := User{ID: id, Email: email, Name: "Test User", Active: true}
    for k, v := range overrides {
        switch k {
        case "name":
            u.Name = v.(string)
        case "active":
            u.Active = v.(bool)
        }
    }
    return u
}
```

A shared fakers helper (generic override application over a struct) makes these faster to
write and keeps them uniform across packages.

## Dependency direction at a glance

| Role | May import |
|---|---|
| Core (domain) | stdlib, helpers |
| Core services | stdlib, core, ports, helpers |
| Ports | stdlib, core, helpers (interfaces + their DTOs) |
| Outbound adapter | stdlib, core, ports, helpers, **+ the external tech it adapts** |
| Inbound adapter | anything (couples directly to concrete services) |
| Helpers | stdlib, other helpers, generic external libs (no mockable side-effect, no domain coupling in the used surface) |

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
ports, outbound adapters — receives that config as **injected parameters** and must
never read the environment itself.

This is the same "don't assume how you're driven" rule applied to config: an outbound adapter
that reads `PIPEDRIVE_TOKEN` from the environment wouldn't work when driven by an Android or
desktop entrypoint that has no such env var. A strong tell is **asymmetry** — one value handed
in as a constructor parameter while another is read from the environment in the same
constructor. Reading env inside an inner layer is a common but wrong shortcut; the fix is
always to read it at the entrypoint and inject the value.

> Note: It is ok to have a generic helper that wraps the behavior of reading env vars as long
> as this helper is only used on the inbound layer.

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
  miss — spend judgment there. Also check two more coupling classes an import linter cannot
  see:
  - **Adapters (in- or outbound) leaking external representation *into* the domain** —
    passing a timestring instead of `time.Time`, a seconds `int` instead of
    `time.Duration`, or handing over an external enum/value without translating it to a
    domain type. The adapter must translate at its boundary, not push the raw external
    shape inward.
  - **Core services implementing what belongs in an adapter** — building an HTTP header map
    and forwarding it, translating an internal enum to an external wire format before
    handing it to an adapter, or defining SQL / AI prompts (complex external languages)
    inside a service. These belong hidden inside adapters; the service should call
    well-defined functions instead. (Forwarding an opaque, user-provided prompt as a blob
    is fine — a blob doesn't contaminate the service's logic.)
  - **Anything defined in core that is coupled to external system** — enum values
    that match perfectly with external tecnologies to avoid having to translate it.
    DTOs that are only used to receive or send messages to an external systems and
    don't represent internal domain concepts.
    - **One Exception:** As long as we control the database schema to match our domain
      models its ok not to have a translation step between core and the db. DB tags
      are also allowed on entities as long as the entities are not made to fit the db
      but the other way around.
- **A lint-config generator:** map each module to a role, then emit allowed-import sets
  from the table. The role boundaries are mechanical; the delivery-coupling rule stays with
  the reviewer.
