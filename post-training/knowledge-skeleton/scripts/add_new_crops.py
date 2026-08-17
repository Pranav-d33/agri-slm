#!/usr/bin/env python3
"""Add 30 researched crop entities + crops.horticulture.ornamentals category to crops.json."""
import json


CROPS = "data/crops.json"
SPEC = json.load(open("/tmp/new_crops_spec.json"))
del SPEC["notes"]
STATE = json.load(open("/tmp/state_ids.json"))

c = json.load(open(CROPS))
eids = {e["id"] for e in c["entities"]}

def sr(rid):
    return {"id": spec[rid]["src"], "url": spec[rid]["url"]}

spec = dict(SPEC)
# validate all state names exist
for rid, s in spec.items():
    for st in s["states"]:
        if st not in STATE:
            raise SystemExit(f"{rid}: unknown state {st!r}")

added = 0
for rid, s in spec.items():
    if rid in eids:
        continue
    ent = {
        "id": rid,
        "name": s["name"],
        "type": "entity",
        "domain": "crops",
        "attributes": {"type": s.get("note") or s["name"], "scientific_name": s["scientific"]},
        "relations": [
            {"predicate": "is_a", "object": ".".join(rid.split(".")[:-1])}
        ] + [
            {"predicate": "grown_in", "object": STATE[st], "source": sr(rid)}
            for st in s["states"]
        ],
        "source": {"id": s["src"], "url": s["url"]},
    }
    c["entities"].append(ent)
    eids.add(rid)
    added += 1

# add crops.horticulture.ornamentals category
if "crops.horticulture.ornamentals" not in eids:
    c["entities"].append({
        "id": "crops.horticulture.ornamentals",
        "name": "Ornamental Plants",
        "type": "entity",
        "domain": "crops",
        "attributes": {"type": "Ornamental/garden plants grown for display"},
        "relations": [{"predicate": "is_a", "object": "crops.horticulture"}],
        "source": {"id": "icar", "url": "https://icar.org.in/"},
    })
    added += 1

json.dump(c, open(CROPS, "w"), indent=1, ensure_ascii=False)
print(f"added {added} entities -> total {len(c['entities'])}")