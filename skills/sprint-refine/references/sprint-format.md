# Sprint Format Spec (sprint-refine)

This is the canonical output format for refined sprints. Both the Leader and the Reviewer MUST load and enforce this spec. Output is GitHub-Flavored Markdown (GFM) — rendered as checkboxes on GitHub.

## Language

Write the sprint in the SAME language as the input sprint — never translate task content. This spec and the skill are in English, but the output sprint must match the input's language (e.g., a Portuguese input stays Portuguese).

## Checkboxes

Every done-markable item uses the GFM checkbox syntax:
- `- [ ]` — open (to do)
- `- [x]` — closed (done)

Non-task items MAY also carry `- [ ]` when you want to track that a specific detail was seen/implemented.

## Nesting

Items nest to multiple levels. Use **2-space indent** per level:

```
- [ ] Top-level item
  - Sub-item (2 spaces)
    - Sub-sub-item (4 spaces)
```

## Tasks and SP tags

A **task** is any item that carries a Story-Point estimate, at ANY nesting level. One way to break a task down is to promote its sub-items into tasks by giving each its own SP estimate — but that's only one option (see "Breaking tasks down" in `leader.md`: children, root-level siblings, or moving one to another section can all be right depending on how the work groups).

Every task MUST have:
1. A checkbox (`- [ ]`).
2. An SP estimate as an inline code tag at the end of the same line: `` `N SP` ``

Optional: `@assignee` inline after the item text.

Non-task sub-items DO NOT have an SP tag.

**Do not nest estimated tasks.** A task carrying an SP tag must not contain another SP-tagged task among its descendants — it's ambiguous whether the parent's SP already accounts for the children's. When a parent needs to split into estimated pieces, drop the parent's SP tag and make the pieces sibling tasks (nested under a shared unestimated context line, or at the section root).

## Section structure

```
# Sprint Title

## Goals
...

## Tasks

### Group Name   (H3 — a feature name, "Bugs", "Tech Debt", …)

#### Subgroup Name   (H4 or **bold**, optional, for further grouping)

- [ ] Task description `N SP` @assignee
  - Context or detail sub-item
    - [ ] Tracked sub-step (no SP = not a task)
  - Some other detail
- [ ] Update all pipelines:
    - [ ] Pipeline A `1 SP`  (is a task)
    - [ ] Pipeline B `2 SP`  (is a task)
    - [ ] Pipeline C `1 SP`  (is a task)

## Stretch
...

## Backlog
...

## Open Questions
...
```

The fixed H2 sections are **Goals / Tasks / Stretch / Backlog / Open Questions**, plus an optional transient **`## Design decisions`** log (see "Design-decision log" below) removed at publish. Inside `## Tasks`, group related work under H3 (and H4) subsections named freely — feature names, "Bugs", "Tech Debt", "UX Improvements", or whatever splits the current tasks into comprehensible, related groups. Use that nesting when the sprint is large: organize tasks into H3 subgroups rather than leaving them all ungrouped at the top level of `## Tasks`. This is purely about grouping *within* `## Tasks` — it never means moving a task out to a different H2 section (see the scope rule below).

`## Backlog` is **out of scope by default**: only `## Tasks` and `## Stretch` get refined and estimated. Leave backlog items untouched unless the user explicitly asks; tasks change section only on user request, never on the skill's initiative.

## Sub-item granularity

Sub-items exist to make a task scannable — never to hide its size or save lines.

- **One element per sub-item.** When a task enumerates elements (entity fields, migration steps, routes), each element gets its own sub-item. Never pack two elements on one line (`` `a string`, `b string` ``) — mixed sub-items only make reading harder.
- **Inline lists don't scale.** A first line (or sub-item) that enumerates more than 3 elements, or any element with a long description, must be broken into sub-items — even when only 2 elements, if their descriptions are long.
- **Long tasks get sub-checkboxes.** When a task accumulates many sub-items (roughly: doesn't fit on one screen), promote its major sub-items to `- [ ]` tracked sub-steps (no SP tag), or split it into sibling subtasks under an unestimated context line. A wall of unchecked prose is not an acceptable shape for a 3 SP task.

## Stack-context markers

When consecutive tasks in the same section switch stack (backend → frontend, app → infra), make the switch visible: prefix the task title (`Frontend — …`, `Backend — …`) or insert a bold separator line (`**Frontend:**`) before the group. A reader scanning task titles must never discover the stack switch only from the sub-items.

## Task first line

Each task's first line states the concrete *what* in plain terms — the change, the file/screen, the behavior — leaning on the surrounding section/subsection context rather than repeating it. Keep internal jargon and implementation details (method/field names, etc.) out of the first line unless they add clarity; put them as a sub-item if the dev needs them. Sentences that only make sense with the conversation that produced the draft (dropped decisions, "for later" asides) do not belong in the sprint at all.

## Dependencies come first

When a task depends on another, `Depends on: <short task name>` is its **first sub-item** — before any other detail. A dependency has to be read *before* work starts (it decides whether the task can even begin), so it must never be buried under implementation sub-items.

```
- [ ] Add the "generate report" button to the diligence screen `1 SP`
  - Depends on: report-generation route
  - Wires the button to `POST /diligences/:id/report`
  - Disabled until the diligence has at least one approved item
```

## Feature blockquotes — problem first

The rare feature blockquote (`>`) that introduces a larger feature must **open with the problem it solves, in the user's / the flow's terms**, and only then move to the solution and its technical structure. Do NOT open with the structural distinction — that lands on a reader who doesn't yet know why the feature exists. When in doubt, **verbose and clear beats short and obtuse.**

- Bad (opens with structure): "> New entity `Finding` — **not** an extension of `Review`. …"
- Good (opens with the problem): "> Today a review reports a red/yellow flag and that flow has to be fast so the lawyer doesn't forget to report it; but afterwards it has to be investigated in depth and documented — for that we create the `Finding` entity as a follow-up to a review. Structurally it is a new entity, not an extension of `Review`, because …"

## Design-decision log

The sprint may carry a `## Design decisions` (sign-off) section holding the design choices the user locked during refinement. The canonical title is English; when the sprint is written in another language the title may be localized (e.g. `## Decisões de design` in Portuguese) — treat either as this same section. It exists so a paused-and-resumed refinement never re-decides or undoes an accepted choice: the Leader reads it as **binding** at the start of every round and **appends** new decisions as they arise (see `leader.md`). It is the natural source from which genuine recurring patterns are later promoted to the skill's persistent project memory. Whoever publishes the sprint deletes this section; forgetting to is harmless (a stale log in a shipped sprint does nothing).

## Actions, not artifacts

Task titles and sub-items describe ACTIONS to perform (or how the line connects to the rest of the task) — never a bare artifact/noun label. A noun list looks formal but transports less understanding of what must be done and how the pieces connect. Artifact-style labels are acceptable only occasionally as grouping headers for sub-items.

- Bad: "Rota admin-only de emissão" → Good: "Implementar rota admin-only de emissão"
- Bad: "Lista de versões por relatório" → Good: "Adicionar lista de versões e ações por relatório na tela da diligência"
- Bad: "Dependência pdfcpu: adicionar ..." → Good: "Para carimbar o PDF na rota de emissão, adicionar a dependência pdfcpu ..."
- Bad: "Auto-finalização: ao montar a tela ..." → Good: "Ao carregar a tela da diligência, iniciar a finalização de versões em `markdown_ready` ..."

## No planning-process leakage

Internal planning references (rule ids like `fe-027`, reviewer names, round numbers, vote spreads) do not belong in task text — the reader will not use them. State the resulting requirement plainly instead.

Task text is also **attribution-free, persona-free, and date-free**: no "confirmed by X on <date>", no persona nicknames ("shortcut for <persona>"), no decision timestamps inline in a ticket. Who decided something and when belongs in the `## Open Questions` log, not in the implementation bullets — state only the resulting requirement.

**Exemption — the persona-panel log.** The `### Answered by persona panel — override if wrong` subsection under `## Open Questions` is the ONE place persona names and their convergence are required (they exist so the user can veto an auto-resolved answer asynchronously). Do NOT flag persona names, stances, or "which personas converged" there as leakage — that content is mandated by the skill (see SKILL.md Phase 1.5). The attribution/persona/date ban above applies to task text only.

## Section granularity

A section whose title is ~the same as the first line of its single item is too small. Group such items into a broader section (e.g. "Bugs", "Tech Debt", "New Feature …") instead of one section per item.

Avoid adding comments to the beginning of a section (e.g. using blockquotes `>`) that really reference a specific task — anything that references a specific task belongs on the task's first line or as a sub-item. Blockquotes are only for context on a larger feature, and only rarely.

## SP stats block

A Story-Point statistics block at the BOTTOM of the document is allowed and welcome (total SPs, and optionally a per-section breakdown). Use plain text or a simple table. It's generated once at close-out, not maintained every editing round.

## Example

```markdown
### Bugs

- [ ] Cancelling a sale does not remove the financial transaction `2 SP`
- [ ] Old sales generate a zero-value transaction `3 SP`
  - Root cause: `salePrice` is empty on these products (the field did not exist before)
  - Includes a migration to populate `salePrice` on saved sales orders
- [ ] Fix the cypress tests:
  - [ ] `sales-order-listing.cy.js`: "loads the page with stats and data" `1 SP`
  - [ ] `cash-control-listing.cy.js`: "switches back to all reasons" `1 SP`
```

Notes from the example:
- SP sits on the item that is the actual unit of work, at whatever level that is — the parent "Old sales…" task, or each individual cypress-test child.
- An unestimated parent ("Fix the cypress tests:") is a grouping/context line; its estimated children are the tasks (no SP on the parent → no nested estimated tasks).
- Non-checkbox sub-items ("Root cause…", "Includes a migration…") are details of their task, not separate work.
- Assignees via `@user` inline.
