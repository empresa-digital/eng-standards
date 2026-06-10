#!/usr/bin/env python3
"""Eval the reviewer against the library's own `wrong` fixtures.

Each rule that carries a `wrong` code example IS a test case: feed that wrong code to
the reviewer (loaded with the matching packs) and assert the reviewer flags that rule's
`id`. The catch-rate is the number "does the reviewer catch our own rules?".

Runs the real reviewer headlessly via `claude -p`. The fixture is shown in isolation
(no broader repo this run), so rules that fundamentally need repo-wide context to detect
(e.g. reuse-before-adding, one-source-of-truth) are expected to be harder — they are
tagged `repo-context` in the output so the snippet score isn't read as the whole story.

Usage:
  python3 scripts/eval.py                 # all fixtures
  python3 scripts/eval.py --limit 5       # first 5 (cheap smoke run)
  python3 scripts/eval.py --ids go-no-stuttering,go-json-camelcase
  python3 scripts/eval.py --model opus    # reviewer model (default: sonnet)
"""
import argparse
import glob
import re
import subprocess
import sys

import yaml

REVIEWER = open("review/reviewer.md").read()

# File kind + which packs to load, keyed by id prefix. Mirrors AGENTS.md selective
# loading: each kind loads universal + its pack (+ language pack for cross-cutting
# packs like testing). The org profile is appended in build_prompt.
EXT = {
    "vue-": "vue", "db-": "sql", "infra-": "infra", "git-": "git",
    "test-": "test", "plan-": "plan",
}  # default .go
PACKS_FOR = {
    "go": ["universal.yaml", "packs/backend-go.yaml"],
    "vue": ["universal.yaml", "packs/frontend-vue.yaml"],
    "sql": ["universal.yaml", "packs/database.yaml"],
    "infra": ["universal.yaml", "packs/infra.yaml"],
    "git": ["universal.yaml", "packs/git.yaml"],
    "test": ["universal.yaml", "packs/backend-go.yaml", "packs/testing.yaml"],
    "plan": ["universal.yaml", "packs/planning.yaml"],
}
# Code-fence language label per kind (cosmetic; the rule id is what's asserted).
FENCE = {"go": "go", "vue": "vue", "sql": "sql", "infra": "yaml", "git": "sh",
         "test": "go", "plan": "md"}
# Rules whose violation can't be seen in an isolated snippet — need surrounding repo.
REPO_CONTEXT = {
    "u-reuse-before-adding",
    "u-one-source-of-truth",
    "u-follow-local-convention",
    "u-no-dead-scaffolding",
}
ORG_PROFILE = "orgs/empresa-digital.yaml"  # active org for the eval


def kind(rid: str) -> str:
    for pre, k in EXT.items():
        if rid.startswith(pre):
            return k
    return "go"


def load_cases():
    cases = []
    files = ["universal.yaml"] + sorted(glob.glob("packs/*.yaml")) + [ORG_PROFILE]
    for f in files:
        for r in yaml.safe_load(open(f)).get("rules", []):
            w = r.get("wrong")
            if w and w.get("code"):
                cases.append(r)
    return cases


def build_prompt(rule: dict, leak_desc: bool = False, negative: bool = False) -> str:
    k = kind(rule["id"])
    packs = PACKS_FOR.get(k, PACKS_FOR["go"]) + [ORG_PROFILE]
    rules_yaml = "\n\n".join(open(p).read() for p in packs)
    ext = FENCE.get(k, "go")
    # Negative control: feed the GOOD code and assert the reviewer does NOT flag the
    # rule — proves catches are specific, not carpet-bombing.
    w = rule["right" if negative else "wrong"]
    # By default show ONLY the code — the `wrong.description` often states the diagnosis,
    # which would leak the answer. --with-desc opts the context back in.
    ctx = w.get("description", "")
    fixture = f"// context: {ctx}\n{w['code']}" if (leak_desc and ctx) else w["code"]
    return f"""{REVIEWER}

# Rules in scope
{rules_yaml}

# Change under review
EVAL MODE: review this single changed file in isolation; no broader repo is available
this run. Judge from the file and the context comment alone. Emit the report.

File: changed.{ext}
```{ext}
{fixture}
```
"""


def is_flagged(out: str, rid: str) -> bool:
    """True iff the reviewer flagged `rid` as an actual finding.

    A finding is a bracketed `[rid]` in the Blockers/Nits region only — the prose
    pushback sections (from `## Design risks` on) may name rules to clear or caveat
    them, which must NOT count as a flag.
    """
    findings = re.split(r"^##\s*Design risks", out, maxsplit=1, flags=re.M)[0]
    return f"[{rid}]" in findings


def run_reviewer(prompt: str, model: str) -> str:
    # Prompt goes on stdin: --allowed-tools is variadic and would otherwise swallow a
    # positional prompt arg. "" grants no tools (eval is snippet-only, no repo needed).
    p = subprocess.run(
        ["claude", "-p", "--output-format", "text", "--model", model,
         "--allowed-tools", ""],
        input=prompt, capture_output=True, text=True, timeout=300,
    )
    return p.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--with-desc", action="store_true",
                    help="inject wrong.description as context (easier; may leak diagnosis)")
    ap.add_argument("--negative", action="store_true",
                    help="feed the GOOD code; pass = reviewer does NOT flag the rule")
    a = ap.parse_args()

    cases = load_cases()
    if a.ids:
        want = set(a.ids.split(","))
        cases = [c for c in cases if c["id"] in want]
    if a.limit:
        cases = cases[: a.limit]

    mode = "NEGATIVE control (good code; pass = NOT flagged)" if a.negative else "catch"
    print(f"Running {len(cases)} fixtures, {mode}, model={a.model}\n")
    good = bad = 0
    fails = []
    for rule in cases:
        rid = rule["id"]
        out = run_reviewer(build_prompt(rule, a.with_desc, a.negative), a.model)
        flagged = is_flagged(out, rid)
        ok = (not flagged) if a.negative else flagged
        tag = " [repo-context]" if rid in REPO_CONTEXT else ""
        print(f"  {'PASS' if ok else 'FAIL'}  {rid}{tag}")
        if ok:
            good += 1
        else:
            bad += 1
            fails.append(rid)

    total = good + bad
    label = "Specificity (no false flags)" if a.negative else "Catch-rate"
    print(f"\n{label}: {good}/{total} = {good/total*100:.0f}%" if total else "no cases")
    if fails:
        print(("False flags: " if a.negative else "Missed: ") + ", ".join(fails))
        hard = [m for m in fails if m in REPO_CONTEXT]
        if hard and not a.negative:
            print(f"({len(hard)} of the misses are repo-context rules a snippet can't show.)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
