#!/usr/bin/env python3
"""
Parse CWC 'Water and Related Statistics - 2023' Table T4 (page 27): river
basin-wise catchment area, average water resources potential and utilisable
surface water resources. Attaches a water_stats attribute to existing
water.json basin entities (idempotent).

Source PDF: data/_raw/cwc/cwc_water_stats.pdf, Table T4 (BCM).
Only the 20 CWC sub-basins that map to existing skeleton ids are kept;
group/aggregate rows (Total, 'Ganga-Brahmaputra-Meghna' parent) are skipped.
"""

import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "data/_raw/cwc/cwc_water_stats.pdf"
WATER = ROOT / "data/water.json"

SOURCE = {"id": "cwc", "url": "https://cwc.gov.in/sites/default/files/water-and-related-statistics-2023_1.pdf"}

YEAR = "2023"

# Table T4 basin name (normalized) -> water.json entity id.
NAME_TO_ID = {
    "indus": "water.basin.indus",
    "ganga": "water.basin.ganga",
    "brahmaputra": "water.basins.brahmaputra",
    "barak and others": "water.basin.barak",
    "godavari": "water.basin.godavari",
    "krishna": "water.basin.krishna",
    "cauvery": "water.basin.cauvery",
    "subarnarekha": "water.basin.subarnarekha",
    "brahamani and baitarni": "water.basin.brahmani",
    "mahanadi": "water.basins.mahanadi",
    "pennar": "water.basin.pennar",
    "mahi": "water.basin.mahi",
    "sabarmati": "water.basin.sabarmati",
    "narmada": "water.basins.narmada",
    "tapi": "water.basins.tapi",
    "west flowing rivers from tapi to tadri": "water.basin.west_flowing_south_tapi",
    "west flowing rivers from tadri to kanyakumari": "water.basin.west_flowing_south_tapi",
    "east flowing rivers between mahanadi and pennar": "water.basin.east_flowing_mahanadi_pennar",
    "east flowing rivers between pennar and kanyakumari": "water.basin.east_flowing_pennar_kanyakumari",
    "west flowing rivers of kutch and saurashtra including luni": "water.basin.luni",
}

# Rows present in T4 but with no skeleton entity (skipped, reported).
UNMAPPED = {
    "area of inland drainage in rajasthan": "no basin entity in skeleton",
    "minor river draining into myanmar and bangladesh": "no basin entity in skeleton",
}


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def norm_name(s):
    n = s.lower()
    n = re.sub(r"\(.*?\)", "", n)
    n = n.replace("&", "and")           # Mahanadi & Pennar -> and
    n = re.sub(r"^[a-c]\)\s*", "", n)   # 'a) Ganga' -> 'ganga'
    return re.sub(r"\s+", " ", n).strip()


def num(s):
    n = re.sub(r"[*,]", "", s).strip()
    if not n or n == "-" or n.upper() in ("NA", "N.A"):
        return None
    try:
        return float(n.replace(",", ""))
    except ValueError:
        return None


def extract_table(page_text):
    """Return list of {name, catchment, potential, utilisable} from T4 rows."""
    lines = [clean(l) for l in page_text.split("\n")]
    rows, i = [], 0
    n = len(lines)
    while i < n:
        l = lines[i]
        is_sl = bool(re.fullmatch(r"\d{1,2}", l))
        is_sub = bool(re.match(r"^[a-c]\)", l))
        if not (is_sl or is_sub):
            i += 1
            continue
        # header Sl.No. column (1-5) lines near the top are not rows
        if is_sl and i < 20 and l in ("1", "2", "3", "4", "5"):
            i += 1
            continue
        j = i + 1
        parts = [l] if is_sub else []
        while j < n:
            lj = lines[j]
            if lj == "":
                j += 1
                continue
            if re.fullmatch(r"[0-9][0-9,]*(\.[0-9]+)?", lj) or lj in ("-----", "-", "N.A"):
                break
            if re.fullmatch(r"\d{1,2}", lj) or re.match(r"^[a-c]\)", lj):
                break
            parts.append(lj)
            j += 1
        if not parts or j >= n:
            i += 1
            continue
        # parent group row (Ganga- Brahmaputra-Meghna) has no data cells; a)b)c) rows carry it
        if re.match(r"^[a-c]\)", lines[j]):
            i += 1
            continue
        c = num(lines[j])
        pot = num(lines[j + 1]) if j + 1 < n else None
        us = num(lines[j + 2]) if j + 2 < n else None
        rows.append({"name": clean(" ".join(parts)), "catchment": c,
                     "potential": pot, "utilisable": us})
        i = j + 3
    return rows


def main():
    if not PDF.exists():
        print("missing PDF", PDF)
        return 1
    doc = pymupdf.open(PDF)
    page = doc[26]  # page 27 (0-indexed 26) holds Table T4
    text = page.get_text()
    if "Table T4" not in text:
        print("Table T4 not found on page 27")
        return 1

    rows = extract_table(text)
    water = json.loads(WATER.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in water["entities"]}
    changed = unmapped_names = 0
    for r in rows:
        bid = NAME_TO_ID.get(norm_name(r["name"]))
        if bid is None:
            if norm_name(r["name"]) in UNMAPPED:
                unmapped_names += 1
            else:
                print("  NOTE row not mapped:", r["name"], r)
            continue
        e = by_id.get(bid)
        if e is None:
            print("  NOTE id missing in water.json:", bid)
            continue
        e.setdefault("attributes", {})["water_stats"] = {
            "year": YEAR,
            "catchment_area_km2": r["catchment"],
            "avg_water_resources_potential_bcm": r["potential"],
            "utilisable_surface_water_bcm": r["utilisable"],
            "source": SOURCE,
        }
        changed += 1

    WATER.write_text(json.dumps(water, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"T4: {len(rows)} rows parsed, water_stats attached to {changed} basins, {unmapped_names} unmapped dropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())