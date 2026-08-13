# Design Strategies — known simplification moves

A catalog of **strategies that have already earned their place in our projects**, for
the design reviewer (and any engineer) to reach for when a simulation asks "what if we
changed the model?". These are *not rules* — nothing here is a violation when absent.
They are moves to try in a simulation, each with the real-world reasoning that makes it
work. That's why this file lives outside `packs/`.

Each entry: **when it applies → the move → why it works**. Add new entries whenever a
refactor discussion produces a move worth reusing.

## S1 — Think in the real world first

**When:** any modeling decision — new entity, new table, new struct.
**Move:** ask what exists *in the real-world problem*. Artifacts we create for the
machine's convenience — DTOs, value objects, structs mirroring DB tables — do not exist
in the real world, so they don't belong in the domain model; push them to the edge that
needs them. DTOs live next to the border that uses them; DB-table structs that the
domain doesn't need (e.g. join/intermediate tables) stay private to the repo layer, not
declared in core.
**Why:** the domain model stays the size of the *problem*, not the size of the
implementation. Every machine-artifact promoted to core is complexity every reader pays
for forever.

## S2 — Hide storage complexity behind the repo layer

**When:** the database needs more structure than the domain concept has.
**Move:** keep the extra structure private to the repo and expose a single flat
aggregate. Canonical example: `documents` + `document_versions` tables, but outside the
repo only `core.Document` exists — because in reality a document doesn't exist
separately from its versions; the version is *metadata of the document*, not a thing of
its own. The repo flattens on read and fans out on write.
**Why:** storage shape is an implementation choice that will change; domain vocabulary
is the language everyone reasons in. Leaking the former into the latter makes every
consumer pay the storage tax. (This is also the strategy the reports feature abandoned
— exposing `Report` + `LatestVersion *ReportVersion` — which is what made the
inconsistency visible.)

## S3 — Move duplicated business logic into core

**When:** the same business decision is being made in two adapters/handlers, or a
handler is growing decision logic.
**Move:** lift the logic into the core service; adapters translate, core decides.
**Why:** one source of truth for the decision; the duplication was a symptom that a
core concept was missing.

## S4 — Transaction-friendly repo methods (KSQL pattern)

**When:** a repo operation must work both standalone and inside a transaction.
**Move:** declare a public repo method that implements the interface, delegating to a
function that receives the db handle as an argument. The public method passes the
normal db; transactional call-sites pass the transaction — same code path, zero
duplication.
**Why:** the KSQL `Provider` interface makes db and tx interchangeable; receiving it as
an argument makes the function agnostic without a second implementation.

## S5 — Listing endpoints go through the query builder with filter + pagination

**When:** any listing route.
**Move:** a `List<X>Filter` struct + `kbuilder.Query` with `Where`/`WhereIf` and
`Offset: Page*PageSize` / `Limit: PageSize`, via `db.QueryFromBuilder` — the
`ListDocuments` shape.
**Why:** filters and pagination are always eventually needed; the builder gives them
nearly for free, and raw-SQL listings are a simplification that costs more than it
saves within one iteration.

---

*Add the next strategy here when a refactor discussion produces one worth keeping.*
