#!/usr/bin/env python3
"""Schema-check every rule YAML. Used by `make validate` and CI.

Exits non-zero on any violation. Keeps the library trustworthy as rules are added
through reviewed PRs (the feedback loop never auto-merges).
"""
import glob
import sys

import yaml

REQUIRED = {"id", "topic", "severity", "sources", "reason"}
SEVERITIES = {"blocker", "nit"}
ID_PREFIXES = ("u-", "go-", "vue-", "db-", "infra-", "git-", "test-", "plan-", "ed-")


def main() -> int:
    files = ["universal.yaml"] + sorted(glob.glob("packs/*.yaml")) + sorted(
        glob.glob("orgs/*.yaml")
    )
    seen_ids: dict[str, str] = {}
    errors: list[str] = []

    for f in files:
        try:
            doc = yaml.safe_load(open(f)) or {}
        except yaml.YAMLError as e:
            errors.append(f"{f}: YAML parse error: {e}")
            continue

        for r in doc.get("rules", []):
            rid = r.get("id", "<no-id>")
            where = f"{f} [{rid}]"

            missing = REQUIRED - set(r)
            if missing:
                errors.append(f"{where}: missing fields {sorted(missing)}")
            if r.get("severity") not in SEVERITIES:
                errors.append(f"{where}: severity must be one of {sorted(SEVERITIES)}")
            if not str(rid).startswith(ID_PREFIXES):
                errors.append(f"{where}: id must start with one of {ID_PREFIXES}")
            if not r.get("principle") and not (r.get("wrong") and r.get("right")):
                errors.append(f"{where}: needs a 'principle' or a 'wrong'/'right' pair")
            if rid in seen_ids:
                errors.append(f"{where}: duplicate id (also in {seen_ids[rid]})")
            else:
                seen_ids[rid] = f

        print(f"{f}: {len(doc.get('rules', []))} rules")

    if errors:
        print("\nFAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"\nOK: {len(seen_ids)} rules, all valid, unique ids.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
