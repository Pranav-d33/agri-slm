#!/usr/bin/env python3
"""
Validate the knowledge skeleton:
- every entity id is unique across all files
- every relation object resolves to an entity id or a known location id
- every entity carries required fields (id, name, domain, type, relations, source)
- every source id is registered in sources.md
- every location relation resolves to an id present in data/locations/*.json
Exits non-zero on any error. Prints a summary.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REQUIRED = ["id", "name", "domain", "type", "relations", "source"]
KNOWN_PREDICATES = {
    "is_a", "part_of", "found_in", "grown_in", "practiced_in", "produced_in",
    "registered_in", "banned_in", "recommended_for", "controlled_by", "affects",
    "requires", "suited_for", "monitored_by", "regulated_by", "certified_by",
}


def load_entities():
    entities = {}
    for path in sorted(DATA.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in data.get("entities", []):
            if e["id"] in entities:
                print(f"ERROR duplicate id: {e['id']} in {path}")
            entities[e["id"]] = e
    return entities


def load_location_ids():
    ids = set()
    for path in sorted((DATA / "locations").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("countries", "states", "union_territories", "zones", "regions", "districts"):
            for item in data.get(key, []):
                if "id" in item:
                    ids.add(item["id"])
                elif "state" in item:  # districts.json entries carry state names
                    ids.add("location." + re.sub(r"[^a-z0-9]+", "_", item["state"].lower()).strip("_"))
        for s in data.get("states", []):
            for dist in s.get("districts", []):
                if "id" in dist:
                    ids.add(dist["id"])
    return ids


def load_source_ids():
    text = (ROOT / "sources.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\| (\w[\w-]*) \|", text, re.M))


def main():
    errors = 0
    entities = load_entities()
    loc_ids = load_location_ids()
    src_ids = load_source_ids()

    for eid, e in entities.items():
        for field in REQUIRED:
            if field not in e:
                print(f"ERROR {eid}: missing required field '{field}'")
                errors += 1
        # source registration
        src = e.get("source", {})
        if isinstance(src, dict) and src.get("id") not in src_ids:
            print(f"ERROR {eid}: source id '{src.get('id')}' not in sources.md")
            errors += 1
        # relations
        for rel in e.get("relations", []):
            pred, obj = rel.get("predicate"), rel.get("object")
            if pred not in KNOWN_PREDICATES:
                print(f"ERROR {eid}: unknown predicate '{pred}'")
                errors += 1
            if obj not in entities and obj not in loc_ids:
                print(f"ERROR {eid}: relation object '{obj}' ({pred}) not found anywhere")
                errors += 1
            if pred in ("found_in", "grown_in", "practiced_in", "produced_in", "banned_in"):
                if obj not in loc_ids:
                    print(f"ERROR {eid}: location predicate '{pred}' points to non-location '{obj}'")
                    errors += 1

    # location files must use valid ids internally (relations already checked above)
    for path in sorted((DATA / "locations").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("countries", "states", "union_territories", "zones", "regions"):
            for item in data.get(key, []):
                for rel in item.get("relations", []):
                    obj = rel.get("object")
                    if obj not in entities and obj not in loc_ids:
                        print(f"ERROR locations/{path.name}: dangling relation to '{obj}'")
                        errors += 1

    n_entities = len(entities)
    n_relations = sum(len(e.get("relations", [])) for e in entities.values())
    print(f"entities: {n_entities}, relations: {n_relations}, location ids: {len(loc_ids)}")
    if errors:
        print(f"FAIL: {errors} error(s)")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
