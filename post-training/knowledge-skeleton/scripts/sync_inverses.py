#!/usr/bin/env python3
"""Materialize missing inverse edges for declared inverse pairs in schema.json.

For every relation with predicate P where P declares an inverse I, the reverse
edge (object --I-> subject) must exist on the object entity. Edges that are
already present are left untouched; only missing reverse edges are appended,
reusing the source of the forward edge. Idempotent. Runs only on entity
relations (location files not touched).

Pairs handled today: requires<->suited_for, part_of<->has_part.

Run: python3 scripts/sync_inverses.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
INVERSES = {}
for pred, spec in SCHEMA["relation"]["predicates"].items():
    if isinstance(spec, dict) and spec.get("inverse"):
        INVERSES[pred] = spec["inverse"]

# load all entities by id, with the loaded file data for write-back
entities = {}
loaded = {}
for path in sorted(DATA.glob("*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    loaded[path] = data
    for e in data.get("entities", []):
        entities.setdefault(e["id"], (e, path))


def main() -> int:
    added = 0
    # collect edges to add: (target_entity_id, predicate, subject_id, source)
    to_add = []
    for eid, (e, _path) in entities.items():
        for r in e.get("relations", []):
            inv = INVERSES.get(r["predicate"])
            if not inv:
                continue
            obj, src = r["object"], r.get("source")
            target, _tpath = entities.get(obj, (None, None))
            if target is None:
                print(f"SKIP {eid} --{r['predicate']}-> {obj}: object not an entity")
                continue
            existing = {(rr["predicate"], rr["object"]) for rr in target.get("relations", [])}
            if (inv, eid) not in existing:
                to_add.append((obj, inv, eid, src))

    # apply
    touched = set()
    for obj_id, inv, eid, src in sorted(to_add):
        target, path = entities[obj_id]
        edge = {"predicate": inv, "object": eid}
        if src:
            edge["source"] = src
        target.setdefault("relations", []).append(edge)
        touched.add(path)
        added += 1
        print(f"  +{obj_id} --{inv}-> {eid}")

    if added == 0:
        print("no missing inverse edges")
        return 0

    for path in sorted(touched):
        path.write_text(json.dumps(loaded[path], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"added {added} inverse edges across {len(touched)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
