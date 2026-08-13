#!/usr/bin/env python3
"""Reverse-map NARP zones from district attributes.

Districts carrying a `narp_zone` attribute (filled from CRIDA CCP profiles,
source crida-cp) name the zone they belong to. This script links each such
district back to the matching NARP zone via `found_in` relations, resolving
the remaining unmapped zones without inventing data.

A district's narp_zone text is matched to a NARP zone by a keyword map. Only
zones that end up with >=1 district get relations; zones still empty after
this pass remain counted TODOs.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARP = ROOT / "data" / "locations" / "narp_zones.json"
DIST = ROOT / "data" / "locations" / "districts.json"
SRC = {"id": "crida-cp", "url": "https://icar-crida.res.in/ccp.html"}

# zone id suffix -> list of keywords to match against district narp_zone text
# (lowercased). Ordered, first match per district wins.
# Keys are the zone `state` + a zone-label keyword, resolved against zone.state.
ZONE_KEYWORDS = {
    "northern_telangana_zone": ["northern telangana"],
    "southern_telangana_zone": ["southern telangana"],
    "south_arunachal_pradesh_zone": ["south arunachal"],
    "nagaland_meghalaya_hill_zone": ["nagaland", "meghalaya hill"],
    "central_plateau_zone": ["central plateau"],
    "western_plateau_zone": ["western plateau"],
    "south_eastern_plateau_zone": ["south eastern plateau"],
    "south_gujarat_zone": ["south gujarat"],
    "south_gujarat_alluvial_zone": ["south gujarat"],
    "middle_gujarat_zone": ["middle gujarat"],
    "north_gujarat_zone": ["north gujarat"],
    "valley_temperate_zone": ["valley temperate"],
    "cold_arid_zone": ["cold arid"],
    "northeast_transition_zone": ["northeast transition", "north east transition", "northeastern transition"],
    "northeast_dry_zone": ["northeast dry", "north east dry", "north eastern dry", "northeastern dry"],
    "northern_dry_zone": ["northern dry"],
    "northern_transition_zone": ["northern transition", "northern transitional", "nothern transition"],
    "hill_zone": ["hill zone", "hilly zone"],
    "coastal_zone": ["coastal zone", "coastal area"],
    "bastar_plateau_zone": ["bastar plateau"],
    "gird_zone": ["gird"],
    "malwa_plateau_zone": ["malwa plateau"],
    "nimar_valley_zone": ["nimar valley"],
    "jhabua_hills_zone": ["jhabua hills"],
    "sub_montane_zone": ["sub-montane", "submontane"],
}

# each zone label is only valid for specific states (guards keyword collisions)
ZONE_STATES = {
    "northern_telangana_zone": ["Telangana", "Andhra Pradesh"],
    "southern_telangana_zone": ["Telangana", "Andhra Pradesh"],
    "south_arunachal_pradesh_zone": ["Arunachal Pradesh"],
    "nagaland_meghalaya_hill_zone": ["Nagaland", "Meghalaya"],
    "central_plateau_zone": ["Bihar"],
    "western_plateau_zone": ["Bihar", "Jharkhand"],
    "south_eastern_plateau_zone": ["Bihar", "Jharkhand"],
    "south_gujarat_zone": ["Gujarat"],
    "south_gujarat_alluvial_zone": ["Gujarat"],
    "middle_gujarat_zone": ["Gujarat"],
    "north_gujarat_zone": ["Gujarat"],
    "valley_temperate_zone": ["Jammu and Kashmir"],
    "cold_arid_zone": ["Jammu and Kashmir", "Ladakh"],
    "northeast_transition_zone": ["Karnataka"],
    "northeast_dry_zone": ["Karnataka"],
    "northern_dry_zone": ["Karnataka"],
    "northern_transition_zone": ["Karnataka"],
    "hill_zone": ["Karnataka", "Uttar Pradesh", "Himachal Pradesh", "Jammu and Kashmir", "West Bengal"],
    "coastal_zone": ["Karnataka"],
    "bastar_plateau_zone": ["Madhya Pradesh", "Chhattisgarh"],
    "gird_zone": ["Madhya Pradesh"],
    "malwa_plateau_zone": ["Madhya Pradesh"],
    "nimar_valley_zone": ["Madhya Pradesh"],
    "jhabua_hills_zone": ["Madhya Pradesh"],
    "sub_montane_zone": ["Maharashtra"],
}


def state_slug(state):
    import re
    return re.sub(r"[^a-z0-9_]", "", state.lower().replace(" ", "_"))


def main():
    narp = json.loads(NARP.read_text(encoding="utf-8"))
    dist = json.loads(DIST.read_text(encoding="utf-8"))
    zones = narp["zones"]
    zone_by_id = {z["id"]: z for z in zones}

    # zone_rule: zone id -> (label, keywords). Label = id minus 'location.zones.narp_' and state prefix.
    zone_rule = {}
    for z in zones:
        sid = state_slug(z["state"])
        prefix = f"location.zones.narp_{sid}_"
        if z["id"].startswith(prefix):
            label = z["id"][len(prefix):]
        else:
            # fall back to last underscore-token
            label = z["id"].rsplit("_", 1)[-1]
        # find keyword rule by exact label match
        rule = next(((s, k) for s, k in ZONE_KEYWORDS.items() if s == label), None)
        if rule is None:
            # try matching by state + label's leading word (e.g. label 'north_coastal_zone' -> no rule)
            continue
        zone_rule[z["id"]] = (label, rule[1])

    # zone id -> list of district ids (deduped, order preserved)
    zone_districts = {z["id"]: [] for z in zones}
    seen = {z["id"]: set() for z in zones}

    for s in dist["states"]:
        state = s["state"]
        for d in s["districts"]:
            nz = d.get("attributes", {}).get("narp_zone", "")
            if not nz:
                continue
            nz_l = nz.lower()
            for z in zones:
                rule = zone_rule.get(z["id"])
                if not rule:
                    continue
                label, kws = rule
                if state not in ZONE_STATES.get(label, []):
                    continue
                if any(k in nz_l for k in kws):
                    if d["id"] not in seen[z["id"]]:
                        seen[z["id"]].add(d["id"])
                        zone_districts[z["id"]].append(d["id"])
                    break

    # apply found_in relations (skip part_of / existing found_in)
    changed = 0
    for z in zones:
        dids = zone_districts.get(z["id"], [])
        if not dids:
            continue
        existing = {r["object"] for r in z.get("relations", []) if r["predicate"] == "found_in"}
        new = [x for x in dids if x not in existing]
        if not new:
            continue
        for x in new:
            z.setdefault("relations", []).append(
                {"predicate": "found_in", "object": x, "source": SRC}
            )
        z["notes"] = f"found_in {len(existing) + len(new)} district(s)"
        changed += 1

    NARP.write_text(json.dumps(narp, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    # report remaining unmapped
    remaining = [z["id"] for z in zones if not any(r["predicate"] == "found_in" for r in z.get("relations", []))]
    print(f"mapped {changed} zones; remaining unmapped: {len(remaining)}")
    for r in remaining:
        print("  ", r)


if __name__ == "__main__":
    main()
