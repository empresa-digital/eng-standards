---
name: "sprint-refine"
description: "Refines a sprint draft into small (≤3 SP) well-estimated tasks via a subagent cluster (Leader/Reviewer/Clarity-Editor/UX-Critic/Verifier/3 Evaluators) with a cost guard."
---

# sprint-refine

Refines a sprint draft into small, well-ordered, estimated tasks using a subagent cluster that simulates a dev team (refinement + planning poker).

## When to use

When invoked as `sprint-refine <sprint-file> [instruction]`. No instruction = the whole in-scope sprint (all tasks under `## Tasks` and `## Stretch`). With instruction = restricted scope (e.g., "only task X", "only what changed since the last commit").

**`## Backlog` is out of scope by default** — the skill does NOT refine, estimate, or reorder backlog items. It only touches them if the user explicitly asks. A task moves between sections (Tasks ↔ Stretch ↔ Backlog) only on user request (typically a `FIX:` directive), never on the skill's own initiative.

Edits the sprint file **in place** and uses **git** as the history mechanism: one checkpoint commit before refinement starts (documenting the human-authored state) and one commit after it finishes (documenting the skill's changes). Commits touch ONLY the sprint file — never other files in the tree. Does NOT push and does NOT open GitHub issues; the requester reviews the final diff (`git diff HEAD~1 -- <sprint-file>`) and reverts/amends if needed.

## Roles

- **Manager** = you (main session). Single point of contact with the user. Orchestrates, aggregates questions, relays answers, tracks cost. Does NOT read code or large files — only conclusions from subagents.
- **Leader** (subagent, `sonnet`): edits the sprint file in place via targeted diffs, never rewriting the whole file. May read target repo code when precision is needed.
- **Reviewer** (subagent, `sonnet`): critiques form/structure — short bullets, sections, priority/dependency order, blockquote usage, section granularity, code snippets in fenced blocks. Does NOT opine on scope.
- **Clarity-Editor** (subagent, `opus`): adversarial prose editor. Spawned **fresh every Phase-2 round** (no anchoring, no ownership), scoped to ONLY the sections the Leader changed that round + the static-pack digest. Applies the cold-reader test (would a dev who never saw the draft/conversation know what to build?) and returns concrete rewrite diffs. This is the one place a strong model earns its cost — strong-model authoring quality on the prose, without carrying the Leader's whole context or the complacency of an end-only polish pass. Discarded after returning.
- **UX-Critic** (subagent, `sonnet`): challenges the user-facing flow the draft proposes (e.g. block input inline vs. open a dialog) and offers a better path. Spawned in Phase 2 **only when the sprint/scope touches UI or a user-facing flow**. Does NOT vote SP or check form.
- **Verifier** (subagent, `sonnet`): stateless code + facts auditor. Spawned in Phase 1 (and re-spawned when the Leader adds tasks that reference code). Checks every factual claim the sprint makes: local/codebase claims against real code, and external/third-party claims (API limits, library API surface, service contracts) against official documentation via `web_search`/`web_fetch`. Also runs a proactive **reuse scan** on UI tasks (existing components/logic the task would duplicate). Returns a findings list only — no opinions on scope/SP/architecture. `unknown` external claims become Open Questions in the sprint. Discarded after returning findings to keep the long-lived Leader's context lean. Requires web tools (`web_search`, `web_fetch`) available in its spawn.
- **Evaluators ×3** (subagents, `haiku`): vote SP per task. **Stateless: fresh instance each round** (anti-anchoring). Distinct lenses: backend/correctness, infra/operations, risk/edge-cases.
- **Personas ×3** (subagents, `sonnet`, fresh per run): stakeholder simulators that triage Phase-1 questions before they reach the user (see Phase 1.5). Each impersonates a concrete stakeholder matched to the sprint's domain — e.g. a product owner (for a legal-tech sprint, a lawyer-user), a hands-on operator for infra work. Prefer personas already documented in the target repo's CLAUDE.md/AGENTS.md; invent domain-appropriate ones when the documented set doesn't fit (an infra question is not for a lawyer). Role prompt: `references/persona.md`.

Expensive models enter the subagent flow only as the Clarity-Editor (`opus`), scoped to the round's diff. Every other role stays on cheap models.

## Artifacts

- The sprint file itself — edited in place; history lives in git (checkpoint commit before, result commit after).
- `static-pack.md` — digest of README + CLAUDE.md/AGENTS.md of the **target repo** (not the directory where the sprint lives). Does NOT include the sprint itself. Lives in the temp dir `${TMPDIR:-/tmp}/sprint-refine-<target-repo-name>/` (or the OS equivalent), NOT next to the sprint: it is fully regenerable, so it must not pollute the sprint directory or its git history. The deterministic path keeps cross-run reuse working.

The target repo is different from the sprint directory. Before Phase 0, ask the user OR infer from the directory name/sprint content which repo(s) to target. When ambiguous, ask in a batch alongside Phase 1.

Agents receive: static pack + relevant sprint excerpt. Evaluators: the task being voted on + its direct dependencies + the enclosing section/subsection titles (the surrounding context a task inherits from its place in the hierarchy — so a ticket doesn't have to repeat it). This excerpt is embedded **verbatim in the evaluator's spawn prompt** — do NOT hand an evaluator the sprint file path with a "read only section N" instruction; scoped-by-pointer leaks (the evaluator reads the whole file and votes out-of-scope tasks). Leader/Reviewer: the current sprint file read from disk.

## Subagent invocation

Use whatever subagent mechanism the current harness provides — `sessions_spawn` on OpenClaw, the Agent tool on Claude Code. The roles, models, and stateless/reuse rules below are harness-agnostic; map them onto the available primitive.

For stateless evaluators: fresh spawn each round, context isolated, model `haiku`. For Leader/Reviewer: may reuse the same session between rounds if context is still relevant; model `sonnet`. For Verifier and Clarity-Editor: always a fresh spawn (Verifier `sonnet`, Clarity-Editor `opus`). UX-Critic: fresh spawn when UI is in scope, model `sonnet`.

Each spawn brief (always): objective, role prompt (see `references/`), files to read (static pack + sprint excerpt), write-scope (Leader = the sprint file; all critics/Evaluators/Verifier = none), expected output (structured), stable `taskName`.

If the harness supports it, run long work in the background and yield to keep the channel responsive. Run the Phase-2 critics (Reviewer + Clarity-Editor + UX-Critic) in parallel.

## Flow

### Phase 0 — Setup

1. **Git checkpoint.** The sprint file is edited in place; git carries the history.
   - The sprint file must live in a git repository. If it doesn't, STOP and ask the user (offer `git init` or a different location) — do not silently fall back to file copies.
   - If the sprint file has uncommitted changes (or is untracked), commit it — ONLY it (`git add <sprint-file>` — never `-A`; any other dirty files belong to someone else) — with a message like `sprint-refine: checkpoint — human edits before refinement`. If the file is clean, its state is already recorded; no checkpoint commit needed.
   - Record the checkpoint SHA; the pre-refinement version is always recoverable via `git show <sha>:<path>`.

2. **Resolve target repo.** Ask the user if ambiguous. Multiple repos (e.g., back + front) → one pack per repo (`static-pack-<name>.md`).

3. **Decide whether to regenerate the static pack** (at its temp-dir path, see Artifacts) by comparing the current state of the target repo(s) with what is recorded in the pack header:
   - Header line 1: `<!-- repo: <path> | commit: <sha> | dirty: <true|false> | generated: <iso-date> -->`
   - Regenerate if: file doesn't exist; OR `git -C <repo> rev-parse HEAD` != recorded commit; OR `git -C <repo> status --porcelain` is non-empty (dirty); OR mtime of README/CLAUDE.md/AGENTS.md > generated.
   - Otherwise reuse.

4. When regenerating: Leader reads README + CLAUDE.md + AGENTS.md (and any obvious top-level context file) of the target repo and writes the pack to its temp-dir path with the header above on line 1.

### Phase 1 — Understanding + questions (batch)

1. Spawn Leader + Verifier + 3 Evaluators in parallel, each reading pack + sprint scope. Their Phase-1 job is only to surface questions (non-blocking) — nobody edits or votes yet:
   - Leader: questions that block refinement.
   - Verifier: checks every factual claim in the sprint — local/codebase claims against real code, and external/third-party claims against official docs via web search — plus a proactive reuse scan on UI tasks (flag existing components/logic a task would otherwise duplicate). Returns its findings list. (The Verifier reads code; the reuse-finding is later fed to the Leader, and only as a short finding to the UX-Critic if relevant — the UX-Critic never reads backend files itself.)
   - Evaluators: flag anything that would block estimating a task (missing info they'd need to vote). They do NOT vote here — SP voting is Phase 3, one task at a time.
2. Manager consolidates questions in session memory, grouped by task. Manager folds Verifier corrections into the question batch: confirmed facts are noted; wrong/missing claims become questions if they need user input, or are queued as Leader edits if the fix is unambiguous.
3. **Phase 1.5 — Persona triage (before anything reaches the user).** Manager spawns 3 Personas (fresh, in parallel) and gives each the full question batch + static pack:
   - Persona selection: reuse personas documented in the target repo's CLAUDE.md/AGENTS.md when they fit the sprint's domain; otherwise create appropriate ones (product owner matching the product's real users, technical operator for infra, etc.). Mixed sprints may split the batch — each question goes to the 3 personas most qualified to answer it.
   - Each persona answers each question with a stance + confidence (`high`/`low`) + 1-line rationale.
   - **Auto-resolve rule:** if ≥2 personas converge on materially the same answer with `high` confidence, adopt that answer — the question does NOT go to the user. The Leader applies it like a user answer.
   - **Never auto-resolve** questions whose answer depends on facts only the user can know: business priorities/sequencing, commitments to clients or partners, budget, credentials/access, and anything a persona could only guess at. Personas simulate judgment, not knowledge — a confident persona consensus on a knowledge question is still a guess.
   - Every auto-resolved question is logged in the sprint under `## Open Questions` in a `### Answered by persona panel — override if wrong` subsection (question, adopted answer, which personas converged), and summarized in the final message, so the user can veto asynchronously (a veto is just a `FIX:` on the next run).
4. Manager sends ONE message to the user with the remaining questions. User replies in bulk.
5. Manager relays answers; new round only on affected tasks (does not restart everything).

**FIX: annotations.** The input sprint may contain inline annotations prefixed `FIX:` (as well as ordinary inline comments). Every `FIX:` is an AUTHORITATIVE directive from the user. During Phase 1:
- Route any `FIX:` that makes a claim about the codebase to the Verifier.
- If acting on a `FIX:` raises a new question or an open decision (it's ambiguous, or resolving it needs the user's input), add THAT question to the Phase-1 question batch.
- Queue unambiguous `FIX:` directives as Leader edits for Phase 2.

### Phase 2 — Editing + review

1. Leader edits the sprint file via targeted diffs: sections, headings, short sub-bullets under each task, inline snippets when necessary, ordering by (1) priority, (2) dependencies before dependents. Loads and enforces `references/sprint-format.md`. Treats the draft as suspect (rewrites to stand alone, strips conversation-only context).
2. Leader applies all Verifier corrections (wrong facts, missing info, reuse findings) and all resolved `FIX:` directives. Resolved `FIX:` annotations are removed or folded into corrected task text.
3. Three critics run **in parallel** over the sections changed this round → Leader fixes → re-run until both the Reviewer and the Clarity-Editor return `APPROVED`:
   - Reviewer (form/structure against `references/sprint-format.md`).
   - Clarity-Editor (`opus`, fresh spawn, cold-reader test, rewrite diffs).
   - UX-Critic (only if UI/flow in scope; else skip).
4. **Cap: 3 rounds.** If unanimous approval isn't reached in 3 rounds, the Manager reports the deadlock to the user instead of looping.

### Phase 3 — SP voting

1. For each task in scope: spawn 3 **fresh** Evaluators (stateless), each with their lens. Each votes SP + 1-line justification. **Votes in parallel.**
2. **Large task** (median > 3 SP): Leader breaks into subtasks → back to Phase 2 for the new ones → re-vote. **Cap: 2 break cycles per task.** If still over, mark `[NEEDS-SPLIT]` and continue.
3. **Divergence** (range > 2 SP, or a vote > 2× median): outlier explains, others counter, Leader judges. Distant votes are usually just misunderstandings — resolving the misunderstanding almost always refines the ticket further, so the outcome is an edit, not just a number:
   - High voter right → there was a missing detail; Leader edits the task to surface it (break if needed) → re-vote.
   - Low voter right → the high vote was a misunderstanding; Leader specifies the ambiguous part in the task so the next reader doesn't trip on it → re-vote.
   - Both have good points → ask the HIGH voter how they would split the task into subtasks (they see the hidden complexity); Leader breaks accordingly to reduce vote entropy → re-vote the pieces.
4. Final SP = median of valid votes.

### SP anchors (1 SP = 1 day)

The day-based rubric (0.5 / 1 / 2 / 3 / >3 SP) lives in each Evaluator's role prompt (`references/evaluator-*.md`) — it is NOT re-injected from here, so the two stay in sync in one place. The Manager only needs the derived rule: **median > 3 SP → break the task** (a `>3 SP` vote means schema migration, new external integration, or design uncertainty).

Estimates are an internal planning tool (to decide what to break down); they do not need to be exposed to the wider team.

### Phase 4 — Close-out

1. **SP stats block.** Manager generates the Story-Point stats block at the BOTTOM of the sprint once here (total + optional per-section breakdown) — not maintained by the Leader/Reviewer every editing round.
2. **Confidence-driven extra round (in-run, actionable — not a report for the user).** Before handing off, the Manager reviews where the cluster had low confidence (tasks with unresolved Verifier `unknown`s, wide SP divergence, Clarity-Editor rewrites that didn't fully land, UX calls left open). If low-confidence areas remain and the round cap + cost budget allow, run one more targeted Phase-2/3 round on just those tasks instead of shipping them shaky.
3. **Result commit.** Commit the refined sprint file — ONLY it — with a message summarizing what the run did (e.g. `sprint-refine: broke task X into 3, resolved N questions, +SP stats`). Report both SHAs (checkpoint + result) in the final message so the user can review with `git show <result-sha>`.
4. **Skill meta-notes → eng-standards feedback loop.** Draft short meta-notes (kept in session memory — no file on disk) capturing how the *skill* performed — harness friction, rules that didn't fire, recurring FIX-type patterns, jargon/context-leak that slipped through. This is about improving the skill, NOT a summary of the sprint for the user to read (the user reviews the sprint diff directly). Then:
   - **Scrub all client/business content** — no client names, screen names, file paths, business logic, or confidential data. Post only the generic pattern (e.g. "Leader carried conversation-only context into N tickets" → candidate rule), never the specifics of this sprint.
   - Append it as a comment on the eng-standards `improvements` issue (`gh issue list --label improvements --state open --limit 1` in the eng-standards repo), tagged `[sprint-refine]` so the distill bot routes it to its skill-feedback track (proposes edits to the skill's own files, not the rule packs).

## Cost guard (mandatory)

After **each completed phase** (and within Phase 2/3, every 2 rounds), Manager tallies tokens spent and maintains a running total in session memory. Default to **summing the tokens each subagent reports on completion** — a harness token-status call (e.g. `session_status`) may omit spawned-subagent usage, so don't rely on it alone.

**Hard limit: ~$5 USD in tokens per run.** Quick estimate (opus $15/MTok in, $75/MTok out; sonnet $3/$15; haiku ~$1/$5):
- The Clarity-Editor is the cost driver to watch — Opus on the round's changed sections. For this skill, ~500k–1M total mixed tokens is a yellow flag.

Checkpoints:
- **>$3 (60%)**: Manager informs the user ("Spent ~$X so far, estimated $Y to finish"), continues.
- **>$5 (100%)**: Manager **PAUSES** automatically. Reports to the user: what was done, what remains, cost spent. Waits for explicit authorization to continue.

If the Phase-1 estimate already signals a >$5 run, pause before starting Phase 2/3.

## Anti-cost caps (beyond the cost guard)

- 3 review rounds (Phase 2), critics in parallel.
- 2 break cycles (Phase 3).
- Static pack reused when the target repo hasn't changed (commit hash + dirty + mtime).
- Sprint file always edited in-place, never re-emitted in chat output.
- Evaluators receive only the task being voted on + dependencies, not the full sprint.
- Questions to the user always in batch, 1 message per round.

## Output

- Refined sprint file in place, closed by the result commit (see Phase 4): sections + short bullets/sub-bullets, ordered tasks, each task with its SP and explicit dependencies.
- Unresolved `FIX:` annotations and open questions → `## Open Questions` section at the end of the sprint file.
- Final message to the user: high-level summary of what changed (not a diff), cost spent, blockers if any, the checkpoint and result commit SHAs, and confirmation that the scrubbed skill meta-notes were posted to the eng-standards `improvements` issue (Phase 4).

## Role prompts

See `references/leader.md`, `references/persona.md`, `references/reviewer.md`, `references/clarity-editor.md`, `references/ux-critic.md`, `references/verifier.md`, `references/evaluator-backend.md`, `references/evaluator-infra.md`, `references/evaluator-risk.md`. Each spawn loads its prompt as system/objective.

## Recorded decisions

- Static pack reused when target repo unchanged; check via header `commit/dirty/generated` + `git rev-parse HEAD` + `git status --porcelain` + mtime of README/CLAUDE.md/AGENTS.md.
- Evaluators stateless, re-spawned each round, distinct lenses.
- 1 SP = 1 day; break threshold = 3 SP.
- 3 evaluators; no auto-commit; orchestration is harness-agnostic (OpenClaw `sessions_spawn` / Claude Code Agent tool).
- Cost guard with automatic pause at $5 USD; kept at $5 despite the Opus Clarity-Editor (scoped to the round's diff).
- History via git, not file copies: checkpoint commit (human state) before, result commit after; commits touch only the sprint file; no push. Static pack in the OS temp dir; `questions.md` eliminated (batch message + `## Open Questions` cover it).
- Verifier always a fresh spawn (stateless) + proactive UI reuse scan.
- Clarity-Editor = the only strong-model (Opus) role; fresh every round, scoped to the round's diff, adversarial cold-reader test (avoids the complacency of an end-only polish pass).
- UX-Critic runs only when UI/user-facing flow is in scope.
- Persona panel (3 fresh `sonnet` stakeholder simulators) triages Phase-1 questions: ≥2 high-confidence converging answers auto-resolve judgment questions; knowledge questions (priorities, commitments, budget, credentials) always go to the user; auto-resolutions are logged in the sprint for async veto.
- Every run closes out with a confidence-driven extra round (if needed) + scrubbed skill meta-notes to the eng-standards `improvements` issue, tagged `[sprint-refine]`.
