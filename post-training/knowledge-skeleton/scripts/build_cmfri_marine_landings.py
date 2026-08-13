#!/usr/bin/env python3
"""Enrich fisheries with CMFRI 2025 national marine fish landings.

Source: ICAR-CMFRI "Marine Fish Landings in India 2025" (Booklet Series No.
47/2026), page 6 national resource-group table (tonnes). Encodes into:
  - existing marine species entities get `landings_tonnes_2025`
  - resource groups not yet present are added as new entities under fisheries.marine
  - the marine category gets the national total
Deterministic: only groups present in the source are added; nothing invented.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FISH = ROOT / "data" / "fisheries.json"
SRC = {
    "id": "cmfri-landings",
    "url": "https://eprints.cmfri.org.in/19715/1/Marine%20Fish%20Landings%20in%20India%20-%202025.pdf",
}

# CMFRI 2025 resource group (title as printed) -> (display name, tonnes)
LANDINGS = {
    "Wolf herring": ("Wolf Herring", 11746),
    "Oil sardine": ("Indian Oil Sardine", 253260),
    "Lesser sardines": ("Lesser Sardines", 129609),
    "Hilsa shad": ("Hilsa Shad", 13429),
    "Other shads": ("Other Shads", 30754),
    "Coilia": ("Coilia", 55816),
    "Setipinna": ("Setipinna", 16507),
    "Stolephorus": ("Stolephorus", 80399),
    "Thryssa": ("Thryssa", 29115),
    "Other clupeids": ("Other Clupeids", 66581),
    "Bombayduck": ("Bombay Duck", 96170),
    "Half beaks & Full beaks": ("Half Beaks and Full Beaks", 10038),
    "Flying fishes": ("Flying Fishes", 3539),
    "Ribbon fishes": ("Ribbon Fish", 230099),
    "Horse mackerel": ("Horse Mackerel", 36270),
    "Scads": ("Scads", 75981),
    "Leather-jackets": ("Leather Jackets", 15536),
    "Other carangids": ("Other Carangids", 126158),
    "Indian mackerel": ("Indian Mackerel", 269757),
    "Other mackerels": ("Other Mackerels", 67),
    "Scomberomorus commerson": ("Seer Fish (Scomberomorus commerson)", 32925),
    "Scomberomorus guttatus": ("Seer Fish (Scomberomorus guttatus)", 17256),
    "Scomberomorus lineolatus": ("Seer Fish (Scomberomorus lineolatus)", 5),
    "Acanthocybium solandri": ("Wahoo (Acanthocybium solandri)", 518),
    "Euthynnus affinis": ("Eastern Little Tuna (Euthynnus affinis)", 58949),
    "Auxis spp.": ("Frigate Tuna (Auxis spp.)", 32026),
    "Katsuwonus pelamis": ("Skipjack Tuna (Katsuwonus pelamis)", 21028),
    "Thunnus tonggol": ("Longtail Tuna (Thunnus tonggol)", 3576),
    "Thunnus albacares": ("Yellowfin Tuna (Thunnus albacares)", 20257),
    "Other tunnies": ("Other Tunnies", 1823),
    "Bill fishes": ("Bill Fishes", 20650),
    "Barracudas": ("Barracudas", 37910),
    "Mullets": ("Mullets", 15558),
    "Unicorn cod": ("Unicorn Cod", 238),
    "Odonus niger": ("Redtoothed Triggerfish (Odonus niger)", 38984),
    "Lagocephalus spp.": ("Pufferfishes (Lagocephalus spp.)", 23276),
    "Sharks": ("Sharks", 22368),
    "Skates / Guitarfish": ("Skates and Guitarfish", 1228),
    "Rays": ("Rays", 16151),
    "Eels": ("Eels", 12893),
    "Catfishes": ("Catfishes", 57154),
    "Lizard fishes": ("Lizard Fishes", 67191),
    "Rock cods": ("Rock Cods", 57307),
    "Snappers": ("Snappers", 11106),
    "Pig-face breams": ("Pig-Face Breams", 10137),
    "Threadfin breams": ("Threadfin Breams", 233492),
    "Bullseyes": ("Bullseyes", 35858),
    "Other perches": ("Other Perches", 62745),
    "Goatfishes": ("Goatfishes", 15516),
    "Threadfins": ("Threadfins", 13742),
    "Croakers": ("Croakers", 112426),
    "Silverbellies": ("Silverbellies", 46702),
    "Whitefish": ("Whitefish", 5396),
    "Black pomfret": ("Black Pomfret", 20752),
    "Silver pomfret": ("Silver Pomfret", 25349),
    "Chinese pomfret": ("Chinese Pomfret", 7209),
    "Halibut": ("Halibut", 1074),
    "Flounders": ("Flounders", 262),
    "Soles": ("Soles", 33215),
    "Penaeid shrimps": ("Penaeid Shrimps", 163215),
    "Non-penaeid shrimps": ("Non-Penaeid Shrimps", 141650),
    "Lobsters": ("Lobsters", 1632),
    "Crabs": ("Crabs", 61115),
    "Stomatopods": ("Stomatopods", 6858),
    "Bivalves": ("Bivalves", 3616),
    "Gastropods": ("Gastropods", 4877),
    "Squids": ("Squids", 148595),
    "Cuttlefish": ("Cuttlefish", 95835),
    "Octopus": ("Octopus", 12398),
    "MISCELLANEOUS": ("Miscellaneous (Other Resources)", 189352),
}

TOTAL = 3574226  # national marine landings 2025 (mainland + coastal, excl. L&AM islands)


def slug(name):
    s = name.lower()
    for ch in " ()/&,.-":
        s = s.replace(ch, "_")
    s = "_".join(s.split("_"))
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def main():
    data = json.loads(FISH.read_text(encoding="utf-8"))
    entities = data["entities"]
    marine = next(e for e in entities if e["id"] == "fisheries.marine")

    existing = {}
    for e in entities:
        if e["id"].startswith("fisheries.marine.") and e["type"] == "entity":
            existing[slug(e["name"])] = e["id"]

    added, updated = 0, 0
    for src_name, (display, tonnes) in LANDINGS.items():
        sid = slug(display)
        if sid in existing:
            ent = next(e for e in entities if e["id"] == existing[sid])
            ent.setdefault("attributes", {})["landings_tonnes_2025"] = tonnes
            updated += 1
            continue
        new_id = f"fisheries.marine.{slug(display)}"
        entities.append({
            "id": new_id,
            "name": display,
            "type": "entity",
            "domain": "fisheries",
            "attributes": {"landings_tonnes_2025": tonnes},
            "relations": [
                {"predicate": "is_a", "object": "fisheries.marine"},
                {"predicate": "produced_in", "object": "location.states.gujarat"},
                {"predicate": "produced_in", "object": "location.states.kerala"},
                {"predicate": "produced_in", "object": "location.states.maharashtra"},
                {"predicate": "produced_in", "object": "location.states.tamil_nadu"},
                {"predicate": "produced_in", "object": "location.states.andhra_pradesh"},
                {"predicate": "produced_in", "object": "location.states.west_bengal"},
            ],
            "source": SRC,
        })
        existing[sid] = new_id
        added += 1

    marine.setdefault("attributes", {})["landings_tonnes_2025"] = TOTAL
    marine.setdefault("attributes", {})["landings_tonnes_2025_note"] = (
        "National marine fish landings 2025, ICAR-CMFRI Booklet Series No. 47/2026. "
        "Mainland incl. coastal states; excludes Lakshadweep and Andaman & Nicobar."
    )

    FISH.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"fisheries: added {added} new species entities, updated {updated} existing, total 2025 landings={TOTAL}")


if __name__ == "__main__":
    main()
