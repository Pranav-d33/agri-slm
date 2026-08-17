#!/usr/bin/env python3
"""Deterministic KG fixes for soil/weather/water. Idempotent; run then validate.py."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARP = ("narp-zones", "https://epubs.icar.org.in/ejournal/index.php/AAZ/article/view/65198")
IMD = ("imd", "https://mausam.imd.gov.in/")
ICAR = ("icar", "https://icar.org.in/")


def load(name):
    p = ROOT / "data" / f"{name}.json"
    return p, json.loads(p.read_text(encoding="utf-8"))


def save(p, data):
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def by_id(data):
    return {e["id"]: e for e in data["entities"]}


def rel(pred, obj, src=None):
    r = {"predicate": pred, "object": obj}
    if src:
        r["source"] = {"id": src[0], "url": src[1]}
    return r


def add_rel(ent, r):
    if r not in ent["relations"]:
        ent["relations"].append(r)


def ensure_entity(data, spec):
    if spec["id"] not in by_id(data):
        data["entities"].append(spec)


# ----------------------------------------------------------------------------
# SOIL
# ----------------------------------------------------------------------------
p, soil = load("soil")
s = by_id(soil)
SRC_ICAR = {"id": ICAR[0], "url": ICAR[1]}

# S1 + S2: eroded and sandy problem soil entities
ensure_entity(soil, {
    "id": "soil.problem.eroded", "name": "Eroded Soil", "type": "entity", "domain": "soil",
    "attributes": {"note": "Topsoil and nutrient loss by water/wind erosion; ICAR problem soil. Widespread, concentrated in the Shiwalik foothills and hilly tracts of HP/Uttarakhand and parts of the Deccan plateau."},
    "relations": [
        rel("is_a", "soil.categories.problem_soils"),
        rel("found_in", "location.states.himachal_pradesh"),
        rel("found_in", "location.states.uttarakhand"),
        rel("found_in", "location.states.jharkhand"),
        rel("found_in", "location.states.madhya_pradesh"),
    ],
    "source": SRC_ICAR,
})
ensure_entity(soil, {
    "id": "soil.problem.sandy", "name": "Sandy Soil", "type": "entity", "domain": "soil",
    "attributes": {"note": "Coarse-textured, low water-holding capacity, high infiltration and leaching losses; a problem soil needing organic matter and mulching. Dominant in western Rajasthan and the Kachchh region of Gujarat."},
    "relations": [
        rel("is_a", "soil.categories.problem_soils"),
        rel("found_in", "location.states.rajasthan"),
        rel("found_in", "location.states.gujarat"),
    ],
    "source": SRC_ICAR,
})

# S3: coastal saline states on soil.problem.saline (supported by NARP zones with
# dominant coastal-alluvium soils, incl. the West Bengal Coastal Saline zone)
sal = s["soil.problem.saline"]
for st in ("west_bengal", "tamil_nadu", "kerala", "maharashtra"):
    add_rel(sal, rel("found_in", f"location.states.{st}", NARP))
sal["attributes"]["note"] = ("High soluble salts; coastal (WB Sundarbans, TN coast, Kerala backwaters, "
                             "MH Konkan) and arid areas; reclamation via leaching + drainage")

# S4: fix inverted parent/child of problem-soil category
cat = s["soil.categories.problem_soils"]
cat["relations"] = [r for r in cat["relations"] if r["object"] not in ("soil.saline_alkaline", "soil.peaty_marshy")]
cat["attributes"]["types"] = "Acidic, saline, alkaline/sodic, waterlogged, saline-alkali, peaty/marshy, eroded, sandy"
for child in ("soil.saline_alkaline", "soil.peaty_marshy"):
    add_rel(s[child], rel("is_a", "soil.categories.problem_soils"))

# S5: laterite -> West Bengal (Purulia/Bankura/Birbhum), NARP WB laterite & red soil zone
add_rel(s["soil.laterite"], rel("found_in", "location.states.west_bengal", NARP))

# S6: forest/mountain soil -> NE states + Tamil Nadu (Nilgiris)
fm = s["soil.forest_mountain"]
for st in ("meghalaya", "mizoram", "nagaland", "manipur", "tripura", "tamil_nadu"):
    add_rel(fm, rel("found_in", f"location.states.{st}"))

# S7: red soil is NOT suited to cotton; black/regur already carries suited_for cotton
red = s["soil.red"]
red["relations"] = [r for r in red["relations"]
                    if not (r["predicate"] == "suited_for" and r["object"] == "crops.cotton")]
assert any(r["predicate"] == "suited_for" and r["object"] == "crops.cotton"
           for r in s["soil.black"]["relations"]), "soil.black must already suit cotton"
save(p, soil)

# ----------------------------------------------------------------------------
# WEATHER
# ----------------------------------------------------------------------------
p, wea = load("weather")
w = by_id(wea)
SRC_IMD = {"id": IMD[0], "url": IMD[1]}

# W1: new phenomenon category; re-parent elnino / la_nina / western_disturbances
ensure_entity(wea, {
    "id": "weather.phenomenon", "name": "Weather and Climate Phenomena", "type": "category",
    "domain": "weather",
    "relations": [rel("is_a", "weather"), rel("found_in", "location.india")],
    "source": SRC_IMD,
    "attributes": {"note": "ENSO modes, westerly systems, ocean-atmosphere phenomena"}
})
for eid in ("weather.elnino", "weather.la_nina", "weather.western_disturbances"):
    for r in w[eid]["relations"]:
        if r["predicate"] == "is_a":
            r["object"] = "weather.phenomenon"  # keep affects-monsoon relations intact

# W2: rainfall is a climate element, not an advisory
for r in w["weather.rainfall"]["relations"]:
    if r["predicate"] == "is_a":
        r["object"] = "weather"

# W3: correct GKMS coverage figure (defensible IMD scale)
w["weather.agromet"]["attributes"]["service"] = (
    "IMD Gramin Krishi Mausam Sewa (GKMS): block-level agromet advisories covering ~3000+ blocks "
    "across ~800+ districts via KVKs")

# W4: missing monsoon concepts
monsoon_concepts = [
    ("weather.monsoon_onset", "Monsoon Onset", ["Onset of southwest monsoon"],
     {"onset": "~1 June over Kerala", "note": "Advances northwards over the peninsula; onset defines the kharif sowing window"}),
    ("weather.monsoon_withdrawal", "Monsoon Withdrawal (Retreat)", ["Retreating monsoon"],
     {"period": "Withdrawal begins from extreme NW India in mid-September, complete by mid-October",
      "note": "Retreat marks the transition to the north-east monsoon"}),
    ("weather.monsoon_trough", "Monsoon Trough", [],
     {"note": "Low-pressure belt extending from Ganganagar (Rajasthan) to the Head of the Bay of Bengal; its seasonal shifts drive active and break (dry-spell) phases"}),
    ("weather.monsoon_depression", "Monsoon Depression", [],
     {"note": "Low-pressure systems that form over the Bay of Bengal and move west/north-west; major carriers of monsoon rainfall over central India"}),
]
for eid, name, alis, attrs in monsoon_concepts:
    ensure_entity(wea, {
        "id": eid, "name": name, "type": "entity", "domain": "weather",
        "aliases": alis, "attributes": attrs,
        "relations": [rel("is_a", "weather.monsoon"), rel("found_in", "location.india")],
        "source": SRC_IMD,
    })

ensure_entity(wea, {
    "id": "weather.indian_ocean_dipole", "name": "Indian Ocean Dipole (IOD)", "type": "entity",
    "domain": "weather", "aliases": ["IOD"],
    "attributes": {"note": "Second driver of the Indian monsoon; a positive IOD can offset the El Nino deficit and strengthen monsoon rainfall"},
    "relations": [rel("is_a", "weather.phenomenon"), rel("affects", "weather.monsoon_sw"),
                  rel("found_in", "location.india")],
    "source": SRC_IMD,
})
ensure_entity(wea, {
    "id": "weather.cyclone_seasonality", "name": "Cyclone Seasonality", "type": "entity",
    "domain": "weather",
    "attributes": {"note": ("Two cyclone seasons: pre-monsoon (Apr-May, mainly Bay of Bengal) and "
                            "post-monsoon/NE monsoon (Oct-Dec); the Bay of Bengal sees more cyclones "
                            "than the Arabian Sea (roughly 4:1)")},
    "relations": [rel("is_a", "weather.phenomenon"), rel("found_in", "location.india")],
    "source": SRC_IMD,
})

# W5: seasons
ensure_entity(wea, {
    "id": "weather.seasons.monsoon", "name": "Monsoon Season", "type": "entity", "domain": "weather",
    "attributes": {"period": "June to September (south-west monsoon; kharif)"},
    "relations": [rel("is_a", "weather.seasons"), rel("found_in", "location.india")],
    "source": SRC_IMD,
})
ensure_entity(wea, {
    "id": "weather.seasons.retreating", "name": "Retreating Monsoon Season", "type": "entity",
    "domain": "weather", "aliases": ["Post-monsoon season", "North-east monsoon season"],
    "attributes": {"period": "October to December (retreating / north-east monsoon)"},
    "relations": [rel("is_a", "weather.seasons"), rel("found_in", "location.india")],
    "source": SRC_IMD,
})
save(p, wea)

# ----------------------------------------------------------------------------
# WATER
# ----------------------------------------------------------------------------
p, wat = load("water")
SRC_ICAR_URL = {"id": ICAR[0], "url": ICAR[1]}
SRC_CWC = {"id": "cwc", "url": "https://cwc.gov.in/"}
SRC_PIB = {"id": "pib", "url": "https://pib.gov.in/"}

# Wa1: missing irrigation methods
methods = [
    ("water.flood_irrigation", "Flood Irrigation",
     {"note": "Water spread over the whole field surface; simple but low efficiency (~40-50%); typical for paddy"}),
    ("water.furrow_irrigation", "Furrow Irrigation",
     {"note": "Water guided in furrows between raised beds; suits row crops"}),
    ("water.basin_irrigation", "Basin Irrigation",
     {"note": "Field split into level basins flooded one at a time; used for orchards and paddy"}),
    ("water.check_basin_irrigation", "Check Basin Irrigation",
     {"note": "Level basins separated by low earthen ridges; water held until it infiltrates"}),
    ("water.subsurface_irrigation", "Subsurface Irrigation",
     {"note": "Water applied below the surface (buried pipes / raised water table); curbs evaporation losses"}),
]
for eid, name, attrs in methods:
    ensure_entity(wat, {
        "id": eid, "name": name, "type": "measure", "domain": "water", "attributes": attrs,
        "relations": [rel("is_a", "water.methods")], "source": SRC_ICAR_URL,
    })

# Wa2: missing water sources
sources = [
    ("water.river_lift", "River Lift Irrigation",
     {"note": "Water lifted/pumped directly from rivers to fields; extends canal and river water to higher ground"}),
    ("water.rainwater_harvesting", "Rainwater Harvesting",
     {"note": "Capture and collection of rainfall (roofs, trenches, farm ponds, tanks) for irrigation and groundwater recharge"}),
    ("water.conjunctive_use", "Conjunctive Use of Surface and Groundwater",
     {"note": "Coordinated use of surface and groundwater to optimise supply and check waterlogging and salinity"}),
]
for eid, name, attrs in sources:
    ensure_entity(wat, {
        "id": eid, "name": name, "type": "measure", "domain": "water", "attributes": attrs,
        "relations": [rel("is_a", "water.methods")], "source": SRC_CWC,
    })

# Wa3: PMKSY (schemes.pmksy already exists -> link water-side view to it)
ensure_entity(wat, {
    "id": "water.schemes.pmksy", "name": "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY)",
    "type": "institution", "domain": "water", "aliases": ["Per Drop More Crop"],
    "attributes": {
        "launched": "2015-16",
        "outlay": "~Rs 110,000 crore",
        "per_drop_more_crop": ("Micro-irrigation component subsidising drip and sprinkler systems; "
                               "subsidy of 55% for small/marginal farmers and 45% for others"),
    },
    "relations": [rel("is_a", "water"), rel("part_of", "schemes.pmksy"),
                  rel("found_in", "location.india")],
    "source": SRC_PIB,
})
save(p, wat)

print("SOIL entities:", len(soil["entities"]))
print("WEATHER entities:", len(wea["entities"]))
print("WATER entities:", len(wat["entities"]))