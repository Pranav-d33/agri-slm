#!/usr/bin/env python3
"""Add NARP zone -> district found_in relations for zones verified from
authoritative ICAR-CRIDA District Agriculture Contingency Plan documents.

Verified zones only (source-backed). Zones whose definition is disputed by the
authoritative source (Bihar central plateau, South Arunachal, Nagaland-Meghalaya
hill) are left as counted TODOs — see notes.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARP = ROOT / "data" / "locations" / "narp_zones.json"
DIST = ROOT / "data" / "locations" / "districts.json"

# zone id -> (districts by name, CRIDA source url)
# district names matched case-insensitively against districts.json
ZONE_DISTRICTS = {
    "location.zones.narp_andhra_pradesh_northern_telangana_zone": {
        "state": "Telangana",
        "districts": ["Adilabad", "Kumuram Bheem Asifabad", "Nirmal", "Mancherial",
                      "Karimnagar", "Peddapalli", "Jagitial", "Rajanna Sircilla",
                      "Nizamabad", "Kamareddy"],
        "source": "https://www.icar-crida.res.in/CP/Telangana/AP4-Adilabad%2031.1.2011.pdf",
    },
    "location.zones.narp_andhra_pradesh_southern_telangana_zone": {
        "state": "Telangana",
        "districts": ["Vikarabad", "Medchal Malkajgiri", "Hyderabad",
                      "Yadadri Bhuvanagiri", "Ranga Reddy", "Mahabubnagar",
                      "Nalgonda", "Suryapet", "Narayanpet", "Wanaparthy",
                      "Nagarkurnool", "Jogulamba Gadwal"],
        "source": "https://kpiasacademy.com/southern-telangana-zone/",
    },
    "location.zones.narp_gujarat_south_gujarat_alluvial_zone": {
        "state": "Gujarat",
        "districts": ["Surat", "Bharuch", "Narmada"],
        "source": "https://www.icar-crida.res.in/CP-2012/statewiseplans/Gujarat%20(Pdf)/NAU,Navsari/GUJ%2019-Surat%2031.05.2011.pdf",
    },
    "location.zones.narp_jammu_kashmir_valley_temperate_zone": {
        "state": "Jammu and Kashmir",
        "districts": ["Srinagar", "Kupwara", "Ganderbal", "Shopian", "Bandipora",
                      "Kulgam", "Budgam", "Pulwama", "Anantnag", "Baramulla"],
        "source": "https://www.icar-crida.res.in/CP-2012/statewiseplans/J&K%20(Pdf)/JK3-Baramulla-10.08.12.pdf",
    },
    "location.zones.narp_jammu_kashmir_cold_arid_zone": {
        "state": "Ladakh",
        "districts": ["Leh Ladakh", "Kargil"],
        "source": "https://www.icar-crida.res.in/CP-2012/statewiseplans/J&K%20(Pdf)/JK6-Kargil-10.08.12.pdf",
    },
    "location.zones.narp_karnataka_northeast_transition_zone": {
        "state": "Karnataka",
        "districts": ["Bidar", "Kalaburagi"],
        "source": "https://www.icar-crida.res.in/CP-2012/statewiseplans/Karnataka%20(Pdf)/UAS,%20Raichur/KA4-Bidar%2031.1.2011.pdf",
    },
    "location.zones.narp_maharashtra_sub_montane_zone": {
        "state": "Maharashtra",
        "districts": ["Satara", "Nashik", "Kolhapur", "Pune"],
        "source": "https://www.icar-crida.res.in/CP/Maharastra/MPKVV,%20Rahuri/MH7-NASIK%2031.03.2011.pdf",
    },
}


def main():
    narp = json.loads(NARP.read_text(encoding="utf-8"))
    dist = json.loads(DIST.read_text(encoding="utf-8"))

    # index district id by (state, lowercase name)
    by_state_name = {}
    for s in dist["states"]:
        for d in s["districts"]:
            by_state_name[(s["state"], d["name"].lower())] = d["id"]

    changed = 0
    for z in narp["zones"]:
        spec = ZONE_DISTRICTS.get(z["id"])
        if not spec:
            continue
        existing = {r["object"] for r in z.get("relations", []) if r["predicate"] == "found_in"}
        src = {"id": "crida-cp", "url": spec["source"]}
        added = 0
        for dname in spec["districts"]:
            did = by_state_name.get((spec["state"], dname.lower()))
            if not did:
                print(f"  WARN: district not found: {spec['state']} / {dname}")
                continue
            if did in existing:
                continue
            z.setdefault("relations", []).append(
                {"predicate": "found_in", "object": did, "source": src}
            )
            existing.add(did)
            added += 1
        if added:
            z["notes"] = f"found_in {len(existing)} district(s) (ICAR-CRIDA plan)"
            changed += 1
            print(f"  mapped {z['id']} +{added} -> {len(existing)} total")

    NARP.write_text(json.dumps(narp, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    remaining = [z["id"] for z in narp["zones"]
                 if not any(r["predicate"] == "found_in" for r in z.get("relations", []))]
    print(f"\nmapped {changed} zones; remaining unmapped: {len(remaining)}")
    for r in remaining:
        print("  ", r)


if __name__ == "__main__":
    main()
