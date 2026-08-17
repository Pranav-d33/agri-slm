#!/usr/bin/env python3
"""
Build data/_generated/apy_2021_2026.json from _raw/upag/statewise_apy_2021_2026.csv.

The CSV holds area(000 ha)/production(000 t)/yield(kg/ha) per crop x state x
season x year for 2021-22..2025-26 (source: data.desagri.gov.in APY export,
fetched into _raw/upag/). This script adds the quantitative layer as a
generated artifact (data/_generated/apy_2021_2026.json) and attaches a compact
all-India latest-year summary to each mapped crop entity in crops.json.

Mapping is explicit (name -> skeleton id); unmapped/aggregate rows are skipped
and reported, never invented. Crops/states are matched by exact name.
"""

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "_raw/upag/statewise_apy_2021_2026.csv"
OUT_PATH = DATA / "_generated/apy_2021_2026.json"
CROPS_PATH = DATA / "crops.json"

YEARS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
SEASONS = {"Kharif", "Rabi", "Summer", "Total"}

# CSV crop -> skeleton crop id. Aggregate rows map to None (skipped).
CROP_MAP = {
    "Bajra": "crops.bajra",
    "Barley": "crops.barley",
    "Castorseed": "crops.castor",
    "Cotton": "crops.cotton",
    "Gram": "crops.gram",
    "Groundnut": "crops.groundnut",
    "Jowar": "crops.jowar",
    "Jute": "crops.jute",
    "Lentil": "crops.lentil",
    "Linseed": "crops.linseed",
    "Maize": "crops.maize",
    "Mesta": "crops.mesta",
    "Moong": "crops.green_gram",
    "Nigerseed": "crops.niger",
    "Ragi": "crops.ragi",
    "Rapeseed & Mustard": "crops.mustard",
    "Rice": "crops.rice",
    "Safflower": "crops.safflower",
    "Sesamum": "crops.sesame",
    "Soybean": "crops.soybean",
    "Sugarcane": "crops.sugarcane",
    "Sunflower": "crops.sunflower",
    "Tobacco": "crops.tobacco",
    "Tur": "crops.pigeon_pea",
    "Urad": "crops.black_gram",
    "Wheat": "crops.wheat",
    # unmatched / aggregate rows
    "Cereals": None,
    "Guarseed": None,               # no skeleton entity (guar)
    "Jute & Mesta": None,
    "Nutri/Coarse Cereals": None,
    "Other Pulses": None,
    "Sannhemp": None,               # no skeleton entity
    "Shree Anna /Nutri Cereals": None,
    "Small Millets": None,
    "Total Food Grains": None,
    "Total Oil Seeds": None,
    "Total Pulses": None,
}

# CSV state -> skeleton id. 'All India' kept as "__all_india__" (rolled into crop stats).
STATE_MAP = {
    "Andaman And Nicobar Islands": "location.uts.andaman_nicobar",
    "Andhra Pradesh": "location.states.andhra_pradesh",
    "Arunachal Pradesh": "location.states.arunachal_pradesh",
    "Assam": "location.states.assam",
    "Bihar": "location.states.bihar",
    "Chandigarh": "location.uts.chandigarh",
    "Chhattisgarh": "location.states.chhattisgarh",
    "Dadra And Nagar Haveli": "location.uts.dadra_nagar_haveli_daman_diu",
    "Daman And Diu": "location.uts.dadra_nagar_haveli_daman_diu",
    "Delhi": "location.uts.delhi",
    "Goa": "location.states.goa",
    "Gujarat": "location.states.gujarat",
    "Haryana": "location.states.haryana",
    "Himachal Pradesh": "location.states.himachal_pradesh",
    "Jammu And Kashmir": "location.uts.jammu_kashmir",
    "Jharkhand": "location.states.jharkhand",
    "Karnataka": "location.states.karnataka",
    "Kerala": "location.states.kerala",
    "Ladakh": "location.uts.ladakh",
    "Lakshadweep": "location.uts.lakshadweep",
    "Madhya Pradesh": "location.states.madhya_pradesh",
    "Maharashtra": "location.states.maharashtra",
    "Manipur": "location.states.manipur",
    "Meghalaya": "location.states.meghalaya",
    "Mizoram": "location.states.mizoram",
    "Nagaland": "location.states.nagaland",
    "Odisha": "location.states.odisha",
    "Puducherry": "location.uts.puducherry",
    "Punjab": "location.states.punjab",
    "Rajasthan": "location.states.rajasthan",
    "Sikkim": "location.states.sikkim",
    "Tamil Nadu": "location.states.tamil_nadu",
    "Telangana": "location.states.telangana",
    "Tripura": "location.states.tripura",
    "Uttar Pradesh": "location.states.uttar_pradesh",
    "Uttarakhand": "location.states.uttarakhand",
    "West Bengal": "location.states.west_bengal",
    "All India": "__all_india__",
}


def num(v: str):
    v = v.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main():
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data/_raw/upag/statewise_apy_2021_2026.csv"
    out_path = root / "data/_generated/apy_2021_2026.json"
    crops_path = root / "data/crops.json"

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    mapped = {}      # {crop_id: {state_id: {season: {year: {area,production,yield}}}}}
    skipped = 0
    unmapped_crops = set()
    unmapped_states = set()

    for r in rows:
        crop = (r["Crop"] or "").strip()
        state = (r["State"] or "").strip()
        season = (r["Season"] or "").strip()
        cid = CROP_MAP.get(crop)
        sid = STATE_MAP.get(state)
        if cid is None:
            if crop not in CROP_MAP:
                unmapped_crops.add(crop)
            skipped += 1
            continue
        if sid is None:
            unmapped_states.add(state)
            skipped += 1
            continue
        if season not in SEASONS:
            skipped += 1
            continue

        rec = {y: {} for y in YEARS}
        for y in YEARS:
            a = num(r.get(f"Area-{y}", ""))
            p = num(r.get(f"Production-{y}", ""))
            yd = num(r.get(f"Yield-{y}", ""))
            rec[y] = {"area": a, "production": p, "yield": yd}
        mapped.setdefault(cid, {}).setdefault(sid, {})[season] = rec

    # Sort seasons deterministically; keep Total last
    order = {s: i for i, s in enumerate(list(SEASONS - {"Total"}) + ["Total"])}
    doc = {
        "_description": "Area/Production/Yield by crop x state x season x year (2021-22..2025-26). "
                        "Source: DAC&FW APY export (data.desagri.gov.in). "
                        "Generated by scripts/build_apy.py from data/_raw/upag/statewise_apy_2021_2026.csv. "
                        "'__all_india__' key = national aggregate row from the source; units: "
                        "area lakh ha, production lakh tonnes, yield kg/ha (yield = production/area).",
        "crops": {cid: {sid: {s: mapped[cid][sid][s] for s in sorted(mapped[cid][sid], key=order.get)}
                        for sid in mapped[cid]} for cid in mapped},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"APY: entities-rows mapped, crops: {len(doc['crops'])}, "
          f"skipped {skipped} aggregate/unmapped rows")
    if unmapped_crops:
        print("  skipped crops (no skeleton id):", sorted(unmapped_crops))
    if unmapped_states:
        print("  skipped states:", sorted(unmapped_states))

    # Attach all-India latest-year crop stats to crops.json entities
    attach_crop_stats(root, doc)


def attach_crop_stats(root, doc):
    crops_path = root / "data/crops.json"
    crops = json.loads(crops_path.read_text(encoding="utf-8"))
    changes = 0
    for e in crops["entities"]:
        cid = e["id"]
        if cid not in doc["crops"]:
            continue
        ai = doc["crops"][cid].get("__all_india__")
        if not ai:
            continue
        # latest year with data in the Total season
        total = ai.get("Total") or {}
        yr = {}
        for y in reversed(YEARS):
            v = total.get(y)
            if v and any(v.values()):
                yr = v
                break
        if not yr:
            continue
        e.setdefault("attributes", {})["apy_stats"] = {
            "latest_fy": {k: (v if v is not None else None) for k, v in yr.items()},
            "source": "https://data.desagri.gov.in/",
            "note": "latest available season=Total all-India row (area lakh ha, production lakh "
                    "tonnes, yield kg/ha); full crop x state x season x year series in "
                    "data/_generated/apy_2021_2026.json",
        }
        changes += 1
    if changes:
        crops_path.write_text(json.dumps(crops, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"crops.json: attached apy_stats to {changes} entities")


if __name__ == "__main__":
    main()