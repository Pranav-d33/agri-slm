#!/usr/bin/env python3
"""Deterministic fixes: livestock + fisheries (per task). W >=, 1off r."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

def dump(path, data):
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def find(data, eid):
    for i, e in enumerate(data["entities"]):
        if e["id"] == eid:
            return i, e
    raise KeyError(eid)

# ---------- LIVESTOCK ----------
lv = load(DATA / "livestock.json")

# check for institutions.dpr (task: add developed_by ONLY if it exists)
dpr_exists = False
import glob
for f in sorted(glob.glob(str(DATA / "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    for e in d.get("entities", []):
        if e["id"] == "institutions.dpr":
            dpr_exists = True

_, bhutia = find(lv, "livestock.breed.bhutia")
assert bhutia["type"] == "entity" and bhutia["attributes"]["species"] == "horse"
assert bhutia["source"] == {"id": "nbragr", "url": "https://nbagr.res.in/"}, bhutia["source"]

new_breed = {
    "id": "livestock.breed.bhimthadi",
    "name": "Bhimthadi",
    "type": "entity",
    "domain": "livestock",
    "attributes": {
        "note": "Draught horse, Maharashtra; descended from Arabian/Mongolian stock; official 8th registered horse breed of India (NBAGR, registered Dec 2023)",
        "species": "horse",
    },
    "relations": [
        {"predicate": "is_a", "object": "livestock.horse"},
        {"predicate": "grown_in", "object": "location.states.maharashtra"},
    ],
    "source": {"id": "nbragr", "url": "https://nbagr.res.in/"},
    "aliases": [],
}
assert all(e["id"] != new_breed["id"] for e in lv["entities"]), "bhimthadi already present"
lv["entities"].append(new_breed)

_, vanaraja = find(lv, "livestock.breed.vanaraja")
vanaraja["relations"] = [r for r in vanaraja["relations"] if r["object"] != "institutions.nbagr"]
assert not any(r["object"] == "institutions.nbagr" for r in vanaraja["relations"])
assert not dpr_exists, "institutions.dpr unexpectedly exists"
dump(DATA / "livestock.json", lv)

# ---------- FISHERIES ----------
fh = load(DATA / "fisheries.json")

# 1. ADD common carp mirroring silver_carp
_, silver = find(fh, "fisheries.inland.silver_carp")
assert silver["relations"][0] == {"predicate": "is_a", "object": "fisheries.inland"}
assert silver["source"] == {"id": "nfdb", "url": "https://nfdb.gov.in/"}
common_carp = {
    "id": "fisheries.inland.common_carp",
    "name": "Common Carp",
    "type": "entity",
    "domain": "fisheries",
    "attributes": {
        "note": "Cyprinus carpio; exotic; bottom feeder; third exotic carp in carp polyculture (with silver carp and grass carp)"
    },
    "relations": [
        {"predicate": "is_a", "object": "fisheries.inland"},
        {"predicate": "found_in", "object": "location.india"},
    ],
    "source": {"id": "nfdb", "url": "https://nfdb.gov.in/"},
}
assert all(e["id"] != common_carp["id"] for e in fh["entities"]), "common_carp already present"
fh["entities"].append(common_carp)

# 2. FIX oil_sardine note (CMFRI Marine Landings 2025: mackerel #1, cephalopods #2, oil sardine #3)
_, oil = find(fh, "fisheries.marine.oil_sardine")
oil["attributes"]["note"] = (
    "3rd largest single-species marine catch in 2025 (2,53,119 t) after mackerel (2,70,755 t) "
    "and cephalopods (2,57,767 t); per ICAR-CMFRI Marine Fish Landings 2025; Kerala and TN coast"
)
oil["attributes"]["landings_tonnes_2025"] = 253119
oil["source"] = {
    "id": "cmfri-landings",
    "url": "https://eprints.cmfri.org.in/19715/1/Marine%20Fish%20Landings%20in%20India%20-%202025.pdf",
}

# 3. DELETE stub+2023 duplicates, merging distinct facts first
STUBS = [
    "fisheries.marine.seer_fish_s_commerson",
    "fisheries.marine.seer_fish_s_guttatus",
    "fisheries.marine.seer_fish_s_lineolatus",
    "fisheries.marine.eastern_little_tuna_e_affinis",
    "fisheries.marine.skipjack_tuna_k_pelamis",
    "fisheries.marine.longtail_tuna_t_tonggol",
]
for s in STUBS:
    assert any(e["id"] == s for e in fh["entities"]), f"{s} missing"
fh["entities"] = [e for e in fh["entities"] if e["id"] not in STUBS]

# penaeid: merge 2023 facts into 2025 entities, then delete 2023 versions
_, pe_sh = find(fh, "fisheries.marine.penaeid_shrimps")
pe_sh["attributes"]["note"] = (
    "Penaeid prawns (marine shrimp; Parapenaeopsis, Penaeus spp.); 2023 landings declined 37% vs 2022 (2023 record)"
)
_, np_sh = find(fh, "fisheries.marine.non_penaeid_shrimps")
np_sh["attributes"]["note"] = (
    "Non-penaeids (Acetes spp.); 2.11 lakh t in 2023 (5.98% of marine landings); basis of dried-shrimp industry"
)
OLD_P = ["fisheries.marine.penaeid_prawns", "fisheries.marine.non_penaeid_prawns"]
for p in OLD_P:
    assert any(e["id"] == p for e in fh["entities"]), f"{p} missing"
fh["entities"] = [e for e in fh["entities"] if e["id"] not in OLD_P]

# 4. by_state vs declared-total discrepancy note (keep official total primary)
_, inland = find(fh, "fisheries.inland")
prod = inland["attributes"]["production_lakh_tonnes_fy_2022_23"]
bs_sum = round(sum(v for v in prod["by_state"].values() if v is not None), 2)
assert bs_sum == 130.89, bs_sum
inland["notes"] = (
    "DAHD FY2022-23 inland production declared 131.13 lakh t; the by_state split in this record sums to "
    "130.89 lakh t (diff 0.24, attributed to unreported Sikkim figure and rounding). Official total kept as "
    "primary; split source dahd-fisheries."
)

dump(DATA / "fisheries.json", fh)
print("OK: livestock + fisheries edited")