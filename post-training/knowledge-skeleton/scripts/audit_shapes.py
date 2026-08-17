#!/usr/bin/env python3
"""Audit attribute-shape conformance against the schema.json ontology.

Regenerable report: for every (domain, type) group, counts how many distinct
attribute key-sets exist, lists per-key presence, and flags violations of the
class contract (unknown keys, deprecated aliases, synonym co-presence).

Exit code 0 = report generated. Run: python3 scripts/audit_shapes.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMA = ROOT / "schema.json"

ALIASES = json.loads(SCHEMA.read_text(encoding="utf-8"))["key_aliases"]
ALIASES.pop("_description", None)
ALIAS = {alias: canon for canon, alist in ALIASES.items() for alias in alist}


def all_entities():
    for f in sorted(DATA.glob("*.json")):
        dom = f.stem
        for e in json.loads(f.read_text(encoding="utf-8")).get("entities", []):
            yield dom, e


def main():
    shape = defaultdict(lambda: defaultdict(list))
    violations = []

    for dom, e in all_entities():
        keys = tuple(sorted(e.get("attributes", {}).keys()))
        shape[(dom, e["type"])][keys].append(e["id"])

        for k in keys:
            if k in ALIAS:
                violations.append(("deprecated-key", e["id"], k, f"use '{ALIAS[k]}'"))

        attrs = e.get("attributes", {})
        for canon, alist in ALIASES.items():
            present = [a for a in alist if a in attrs]
            if canon in attrs and present:
                violations.append(("synonym-copresence", e["id"], canon, ",".join(present)))

    print(f"{'domain':<18}{'type':<12}shapes  entities")
    multi = 0
    total = 0
    for (dom, typ), variants in sorted(shape.items()):
        total += 1
        n = sum(len(v) for v in variants.values())
        if len(variants) > 1:
            multi += 1
        print(f"{dom:<18}{typ:<12}{len(variants):>5}  {n:>5}  "
              f"{'MULTI' if len(variants) > 1 else ''}")
        for ks, ids in sorted(variants.items(), key=lambda x: -len(x[1])):
            if len(variants) > 1:
                print(f"    x{len(ids):<4} {list(ks)}")

    print(f"\ngroups with >1 shape: {multi}/{total}")
    print(f"violations: {len(violations)}")
    kinds = defaultdict(int)
    for v in violations:
        kinds[v[0]] += 1
    print(f"  by kind: {dict(kinds)}")
    for v in violations[:20]:
        print("  ", v)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
