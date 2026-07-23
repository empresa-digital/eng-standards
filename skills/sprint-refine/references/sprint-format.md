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

The fixed H2 sections are **Goals / Tasks / Stretch / Backlog / Open Questions**. Inside `## Tasks`, group related work under H3 (and H4) subsections named freely — feature names, "Bugs", "Tech Debt", "UX Improvements", or whatever splits the current tasks into comprehensible, related groups. Use that nesting when the sprint is large; don't keep every task directly under `## Tasks`.

## Task first line

Each task's first line states the concrete *what* in plain terms — the change, the file/screen, the behavior — leaning on the surrounding section/subsection context rather than repeating it. Keep internal jargon and implementation details (method/field names, etc.) out of the first line unless they add clarity; put them as a sub-item if the dev needs them. Sentences that only make sense with the conversation that produced the draft (dropped decisions, "for later" asides) do not belong in the sprint at all.

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
