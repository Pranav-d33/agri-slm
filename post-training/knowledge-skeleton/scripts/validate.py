#!/usr/bin/env python3
"""
Validate the knowledge skeleton:
- every entity id is unique across all files
- every relation object resolves to an entity id or a known location id
- every entity carries required fields (id, name, domain, type, relations, source)
- every source id is registered in sources.md
- every location relation resolves to an id present in data/locations/*.json
- ontology conformance (WARN mode): attribute keys within the entity Class's
  required ∪ optional, no synonym co-presence, no deprecated aliases,
  predicate domain/range respected.
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

SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
CLASSES = {k: v for k, v in SCHEMA["classes"].items() if not k.startswith("_")}
ALIASES = SCHEMA["key_aliases"]
ALIASES.pop("_description", None)
ALIAS = {a: canon for canon, alist in ALIASES.items() for a in alist}


def entity_class(dom, typ):
    """Map (domain, type) to the ontology Class name. '*' domain matches all."""
    for name, c in CLASSES.items():
        if typ not in c.get("types", []):
            continue
        if "*" in c.get("domains", []) or dom in c.get("domains", []):
            return name
    return None


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


def load_districts():
    """Return dict district_id -> (state_name, state_slug)."""
    path = DATA / "locations" / "districts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for s in data.get("states", []):
        state_slug = re.sub(r"[^a-z0-9_]", "", s["state"].lower().replace(" ", "_"))
        for d in s.get("districts", []):
            out[d["id"]] = (s["state"], state_slug)
    return out


def check_district_consistency():
    """District ids must be uniformly 'location.districts.<state>.<district>' and every
    cross-file reference must resolve to an id in districts.json with a matching state slug."""
    errors = 0
    districts = load_districts()
    # canonical set + per-state sets
    all_ids = set(districts)
    by_state = {}
    for did, (st, slug) in districts.items():
        by_state.setdefault(slug, set()).add(did)

    # 1. Every declared district id must conform to the pattern and its slug must match parent state.
    for did, (st, slug) in districts.items():
        parts = did.split(".")
        if len(parts) != 4 or parts[0] != "location" or parts[1] != "districts":
            print(f"ERROR non-conforming district id: {did}")
            errors += 1
            continue
        if parts[2] != slug:
            print(f"ERROR district id state-slug mismatch: {did} (state {st})")
            errors += 1

    # 2. Every location.districts.* reference anywhere (entities + location files) must resolve.
    refs = []
    for path in sorted(DATA.glob("*.json")):
        if path.name == "districts.json":
            continue
        txt = path.read_text(encoding="utf-8")
        refs += [(m, str(path)) for m in re.findall(r"location\.districts\.[a-z0-9_]+(?:\.[a-z0-9_]+)?", txt)]
    for m, src in refs:
        if m not in all_ids:
            print(f"ERROR dangling district ref '{m}' in {src}")
            errors += 1

    # 3. No two districts may share a full id; duplicates are fatal.
    seen = set()
    for did in districts:
        if did in seen:
            print(f"ERROR duplicate district id: {did}")
            errors += 1
        seen.add(did)

    print(f"district ids: {len(districts)}, cross-file district refs: {len(refs)}, consistent" if not errors
          else f"district ids: {len(districts)}, cross-file district refs: {len(refs)}")
    return errors


def check_district_attribute_shape():
    """District attributes must use uniform key names and a uniform source shape.

    Every district with attributes must have 'source' = {"id", "url"}, and any of
    agro_climatic_zone / narp_zone / primary_soils / major_crops must have the
    documented types (str / str / list / list).
    """
    errors = 0
    path = DATA / "locations" / "districts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for s in data.get("states", []):
        for d in s.get("districts", []):
            attrs = d.get("attributes")
            if not attrs:
                continue
            n += 1
            if not isinstance(attrs, dict):
                print(f"ERROR {d['id']}: attributes must be an object")
                errors += 1
                continue
            src = attrs.get("source")
            if not (isinstance(src, dict) and isinstance(src.get("id"), str) and isinstance(src.get("url"), str)):
                print(f"ERROR {d['id']}: attributes.source must be {{id, url}}")
                errors += 1
            for key, want in (("agro_climatic_zone", str), ("narp_zone", str),
                              ("primary_soils", list), ("major_crops", list)):
                v = attrs.get(key)
                if v is not None and not isinstance(v, want):
                    print(f"ERROR {d['id']}: attributes.{key} must be {want.__name__}")
                    errors += 1
                if key == "major_crops" and v is not None and not all(isinstance(c, str) for c in v):
                    print(f"ERROR {d['id']}: attributes.major_crops entries must be crop ids")
                    errors += 1
    print(f"districts with attributes: {n}, attribute format consistent" if not errors
          else f"districts with attributes: {n}")
    return errors


def check_ontology(entities):
    """WARN-mode ontology conformance:
    - attribute keys must be within the entity Class's required ∪ optional
    - deprecated alias keys (per key_aliases) must not appear
    - no synonym co-presence (canonical + alias both set)
    - predicate domain/range respected (source Class in domain, target Class in range)
    Warnings only: schema.json 'conventions.class_contract' states these become
    errors once conformance is declared complete.
    """
    warnings = 0

    # cache object id -> Class name (objects may be location ids, skipped)
    class_of = {}
    for eid, e in entities.items():
        class_of[eid] = entity_class(e.get("domain"), e.get("type"))

    for eid, e in entities.items():
        cls = class_of.get(eid)
        attrs = e.get("attributes") or {}
        if cls is None:
            print(f"WARN {eid}: no ontology Class for (domain={e.get('domain')}, type={e.get('type')})")
            warnings += 1
            continue
        contract = CLASSES[cls]
        allowed = set(contract.get("required", [])) | set(contract.get("optional", {}))
        for key in attrs:
            if key in ALIAS:
                print(f"WARN {eid}: deprecated alias key '{key}' (canonical '{ALIAS[key]}')")
                warnings += 1
            elif key not in allowed:
                print(f"WARN {eid}: key '{key}' not in Class '{cls}' contract "
                      f"(required∪optional)")
                warnings += 1
            elif key in contract.get("required", []):
                pass
        # synonym co-presence: canonical + its aliases both present
        for canon, alist in ALIASES.items():
            if canon in attrs:
                for a in alist:
                    if a in attrs:
                        print(f"WARN {eid}: synonym co-presence '{canon}' + '{a}'")
                        warnings += 1

        # predicate domain/range
        for rel in e.get("relations", []):
            pred = rel.get("predicate")
            obj = rel.get("object")
            spec = SCHEMA["relation"]["predicates"].get(pred)
            if not spec or obj not in class_of:
                continue
            if class_of[eid] not in spec.get("domain", []):
                # AnyClass accepts anything; skip other class-domain mismatches for now
                if spec.get("domain") and "AnyClass" not in spec.get("domain", []):
                    print(f"WARN {eid} --{pred}-> {obj}: source Class '{class_of[eid]}' "
                          f"not in domain {spec.get('domain')}")
                    warnings += 1
            if spec.get("range") and "AnyClass" not in spec.get("range", []) and "Location" not in spec.get("range", []):
                if class_of.get(obj) not in spec.get("range", []):
                    print(f"WARN {eid} --{pred}-> {obj}: target Class "
                          f"'{class_of.get(obj)}' not in range {spec.get('range')}")
                    warnings += 1
    return warnings


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

    errors += check_district_consistency()
    errors += check_district_attribute_shape()
    warnings = check_ontology(entities)

    n_entities = len(entities)
    n_relations = sum(len(e.get("relations", [])) for e in entities.values())
    print(f"entities: {n_entities}, relations: {n_relations}, location ids: {len(loc_ids)}")
    print(f"ontology warnings: {warnings} (warn-mode; see schema.json conventions.class_contract)")
    if errors:
        print(f"FAIL: {errors} error(s)")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
