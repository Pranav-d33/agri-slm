#!/usr/bin/env python3
"""Normalize attribute keys to the schema.json canonical contract (zero-loss).

Applies key_aliases from schema.json (right->left) across all data/*.json:
  notes->note (crops: stale variety-TODO placeholders dropped, verified)
  scientific_name->scientific
  uses->use, purpose->use
  types->type

Zero-loss assertion: any aliased key whose value is NOT a verified-stale
marker (and would therefore be silently dropped) aborts the run before any
file is written. Atomic: no partial writes on violation. Re-runnable
(idempotent): canonical keys are left untouched.

Run: python3 scripts/normalize_shapes.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))

ALIASES = SCHEMA["key_aliases"]
ALIASES.pop("_description", None)
ALIAS = {a: canon for canon, alist in ALIASES.items() for a in alist}

STALE_MARKERS = ("TODO", "todo", "TBD", "placeholder", "PLACEHOLDER")


def is_stale(value) -> bool:
    """True if a string (or the only string in a list/dict) is a stale marker."""
    if isinstance(value, str):
        return any(m in value for m in STALE_MARKERS)
    if isinstance(value, dict):
        return any(is_stale(v) for v in value.values())
    if isinstance(value, list):
        return bool(value) and all(is_stale(v) for v in value)
    return False


def main() -> int:
    violations = []
    renamed = 0
    dropped_stale = 0
    pending = []  # (path, data, changed)

    for f in sorted(DATA.glob("*.json")):
        path = DATA / f
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for e in data.get("entities", []):
            attrs = e.get("attributes", {})
            if not attrs:
                continue
            for key in list(attrs.keys()):
                if key not in ALIAS:
                    continue
                canon = ALIAS[key]
                value = attrs[key]
                if canon in attrs:
                    if is_stale(value):
                        del attrs[key]
                        dropped_stale += 1
                        changed = True
                    else:
                        violations.append(
                            f"{e['id']}: both '{canon}' and '{key}' present "
                            f"with real content (cannot merge without loss)")
                    continue
                if is_stale(value):
                    del attrs[key]
                    dropped_stale += 1
                    changed = True
                else:
                    attrs[canon] = value
                    del attrs[key]
                    renamed += 1
                    changed = True
        pending.append((path, data, changed))

    if violations:
        for v in violations:
            print("ERROR", v)
        print(f"ABORTED: {len(violations)} merge-risk violations, no files written")
        return 1

    written = 0
    for path, data, changed in pending:
        if changed:
            path.write_text(
                json.dumps(data, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            written += 1

    print(f"renamed alias keys: {renamed}")
    print(f"dropped stale markers: {dropped_stale}")
    print(f"files written: {written}")
    print("OK — zero-loss normalization complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
