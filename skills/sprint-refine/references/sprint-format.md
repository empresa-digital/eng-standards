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

A **task** is any item that carries a Story-Point estimate, at ANY nesting level. To break a task down, promote a sub-item into a task by giving it its own SP estimate.

Every task MUST have:
1. A checkbox (`- [ ]`).
2. An SP estimate as an inline code tag at the end of the same line: `` `N SP` ``

Optional: `@assignee` inline after the item text.

Non-task sub-items do NOT need an SP tag.

## Section structure

```
# Sprint Title

## Goals
...

## Section Name   (H2, H3, or **bold**)

### Subsection    (optional)

#### Feature Name (optional, for grouping related tasks)

- [ ] Task description `N SP` @assignee
  - Context or detail sub-item
  - [ ] Tracked sub-step (no SP = not a task)
    - [ ] Sub-sub-step with own SP `1 SP`

## Stretch
...

## Backlog
...

## Open Questions
...
```

## Task first line

Each task's first line states the concrete *what* in plain terms — the change, the file/screen, the behavior. It must carry the ticket on its own. Keep jargon and backend method/field names out of the first line (put them as a sub-item if the dev needs them). Sentences that only make sense with the conversation that produced the draft (dropped decisions, "for later" asides) do not belong in the sprint at all.

## Blockquotes

Blockquotes (`>`) are for context on a **larger feature** only, and only rarely. They MUST NOT carry context for an individual task — that is always a sub-item under the task.

## Section granularity

A section whose title is ~the same as the first line of its single item is too small. Group such items into a broader section (e.g. "Bugs", "Tech Debt") instead of one section per item.

## SP stats block

A Story-Point statistics block at the TOP and at the BOTTOM of the document is allowed and welcome (total SPs, and optionally a per-section breakdown). Use plain text or a simple table.

## Example

```markdown
**Bugs on the sales screens:**

- [ ] Cancelling a sale does not remove the financial transaction `2 SP`
- [ ] Fix old sales generating a zero-value transaction `3 SP`
  - The salePrice field is empty on these products (field did not exist before)
  - [ ] Migration to populate salePrice on saved sales orders
- [ ] Fix cypress tests:
  - [ ] `sales-order-listing.cy.js`: "loads the page with stats and data" `1 SP`
  - [ ] `cash-control-listing.cy.js`: "switches back to all reasons"
```

Notes from the example:
- SP can sit on a sub-item or sub-sub-item; the parent may be unestimated context.
- Non-task items still get `- [ ]` when you want to track they were handled.
- A sub-item without an SP tag (e.g., "switches back to all reasons") is a tracked step, not a task.
- Assignees via `@user` inline.
