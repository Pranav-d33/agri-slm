#!/usr/bin/env python3
"""Fill found_in (zone -> district) relations for NARP zones using ICAR-CRIDA
Contingency Crop Plan district profiles.

Source: https://icar-crida.res.in/ccp.html  (district profile PDFs at
CCP/<state-abbr>/<district>/1.1.pdf which explicitly name the district's
NARP agro-climatic zone).

Only districts with an explicit single-zone assignment are added.  Districts
that CRIDA does not cover, or that span multiple zones, are left untouched
and remain TODO.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONES_PATH = os.path.join(ROOT, "data", "locations", "narp_zones.json")
DISTRICTS_PATH = os.path.join(ROOT, "data", "locations", "districts.json")

# CRIDA folder name -> JSON district name (LGD renames differ).
def lgd_name(state, cridaname):
    renames = {
        "Maharashtra": {
            "Ahmednagar": "Ahilyanagar",
            "Aurangabad": "Chhatrapati Sambhajinagar",
            "Osmanabad": "Dharashiv",
            "Amravathi": "Amravati",
            "Sindhudurga": "Sindhudurg",
            "Raigarh": "Raigad",
            "Thane and phalagar": "Thane",
        },
        "Haryana": {
            "Gurgoan": "Gurugram",
            "Mewat": "Nuh",
            "Sonipet": "Sonipat",
        },
        "Kerala": {
            "Kasargod": "Kasaragod",
            "Trissur": "Thrissur",
        },
        "Himachal Pradesh": {
            "Lahaul & Spiti": "Lahaul And Spiti",
        },
        "West Bengal": {
            "Coochbehar": "Cooch Behar",
            "Uttar-Dinajpur": "Uttar Dinajpur",
            "North 24 parganas": "North 24 Parganas",
            "South 24-Parganas": "South 24 Parganas",
            "Bardhaman": "Purba Bardhaman",  # CRIDA uses undivided Bardhaman
        },
    }
    return renames.get(state, {}).get(cridaname, cridaname)


# CRIDA zone token -> zone JSON id.
ZONE_MAP = {
    "haryana_eastern": "location.zones.narp_haryana_eastern_zone",
    "haryana_western": "location.zones.narp_haryana_western_zone",
    "hp_sub_montane": "location.zones.narp_himachal_pradesh_sub_montane_and_low_hills_zone",
    "hp_mid_hills": "location.zones.narp_himachal_pradesh_mid_hills_sub_humid_zone",
    "hp_high_hills_temperate": "location.zones.narp_himachal_pradesh_high_hills_temperate_zone",
    "hp_high_hills": "location.zones.narp_himachal_pradesh_high_hills_zone",
    "kerala_northern": "location.zones.narp_kerala_northern_zone",
    "kerala_southern": "location.zones.narp_kerala_southern_zone",
    "kerala_central": "location.zones.narp_kerala_central_zone",
    "kerala_high_altitude": "location.zones.narp_kerala_high_altitude_zone",
    "kerala_problem": "location.zones.narp_kerala_problem_area_zone",
    "mh_south_konkan": "location.zones.narp_maharashtra_south_konkan_zone",
    "mh_north_konkan": "location.zones.narp_maharashtra_north_konkan_coast_zone",
    "mh_western_ghat": "location.zones.narp_maharashtra_western_ghat_zone",
    "mh_sub_montane": "location.zones.narp_maharashtra_sub_montane_zone",
    "mh_plain": "location.zones.narp_maharashtra_western_maharashtra_plain_zone",
    "mh_scarcity": "location.zones.narp_maharashtra_scarcity_zone",
    "mh_central_plateau": "location.zones.narp_maharashtra_central_maharashtra_plateau_zone",
    "mh_central_vidharbha": "location.zones.narp_maharashtra_central_vidharbha_zone",
    "mh_eastern_vidharbha": "location.zones.narp_maharashtra_eastern_vidharbha_zone",
    "wb_hilly": "location.zones.narp_west_bengal_hilly_zone",
    "wb_tarai": "location.zones.narp_west_bengal_tarai_zone",
    "wb_old_alluvial": "location.zones.narp_west_bengal_old_alluvial_zone",
    "wb_new_alluvial": "location.zones.narp_west_bengal_new_alluvial_zone",
    "wb_laterite": "location.zones.narp_west_bengal_laterite_and_red_soil_zone",
    "wb_coastal_saline": "location.zones.narp_west_bengal_coastal_saline_zone",
    "an_andaman": "location.zones.narp_andaman_nicobar_islands_andaman_and_nicobar_zone",
    "ld_lakshadweep": "location.zones.narp_lakshadweep_lakshadweep_zone",
    "py_puducherry": "location.zones.narp_puducherry_puducherry_coastal_zone",
    "tm_north_east": "location.zones.narp_tripura_mizoram_manipur_neh_combined_zone",
}

# CRIDA folder name -> zone key.  Only explicit single-zone districts.
ZONE_ASSIGN = {
    "Haryana": {
        "Ambala": "haryana_eastern", "Faridabad": "haryana_eastern",
        "Jhajjar": "haryana_eastern", "Jind": "haryana_eastern",
        "Kaithal": "haryana_eastern", "Karnal": "haryana_eastern",
        "Kurukshetra": "haryana_eastern", "Palwal": "haryana_eastern",
        "Panchkula": "haryana_eastern", "Panipat": "haryana_eastern",
        "Rohtak": "haryana_eastern", "Sonipet": "haryana_eastern",
        "Yamunanagar": "haryana_eastern",
        "Bhiwani": "haryana_western", "Fatehabad": "haryana_western",
        "Gurgoan": "haryana_western", "Hisar": "haryana_western",
        "Mahendragarh": "haryana_western", "Mewat": "haryana_western",
        "Rewari": "haryana_western", "Sirsa": "haryana_western",
    },
    "Himachal Pradesh": {
        "Bilaspur": "hp_sub_montane", "Hamirpur": "hp_sub_montane",
        "Kangra": "hp_sub_montane", "Kullu": "hp_sub_montane",
        "Sirmaur": "hp_sub_montane", "Solan": "hp_sub_montane",
        "Una": "hp_sub_montane",
        "Chamba": "hp_mid_hills", "Mandi": "hp_mid_hills",
        "Shimla": "hp_high_hills_temperate",
        "Kinnaur": "hp_high_hills", "Lahaul & Spiti": "hp_high_hills",
    },
    "Kerala": {
        "Kannur": "kerala_northern", "Kasargod": "kerala_northern",
        "Kozhikode": "kerala_northern",
        "Alappuzha": "kerala_problem",
        "Idukki": "kerala_high_altitude",
        "Ernakulam": "kerala_central", "Malappuram": "kerala_central",
        "Palakkad": "kerala_central", "Trissur": "kerala_central",
        "Wayanad": "kerala_central",
        "Kollam": "kerala_southern", "Kottayam": "kerala_southern",
        "Pathanamthitta": "kerala_southern",
        "Thiruvananthapuram": "kerala_southern",
    },
    "Maharashtra": {
        "Palghar": "mh_north_konkan", "Raigarh": "mh_north_konkan",
        "Thane and phalagar": "mh_north_konkan",
        "Sindhudurga": "mh_south_konkan",
        "Nashik": "mh_western_ghat",
        "Nandurbar": "mh_plain", "Pune": "mh_plain",
        "Ahmednagar": "mh_scarcity", "Aurangabad": "mh_scarcity",
        "Beed": "mh_scarcity", "Dhule": "mh_scarcity",
        "Sangli": "mh_scarcity", "Satara": "mh_scarcity",
        "Solapur": "mh_scarcity",
        "Akola": "mh_central_plateau", "Amravathi": "mh_central_plateau",
        "Buldhana": "mh_central_plateau", "Jalna": "mh_central_plateau",
        "Latur": "mh_central_plateau", "Nanded": "mh_central_plateau",
        "Osmanabad": "mh_central_plateau", "Parbhani": "mh_central_plateau",
        "Chandrapur": "mh_central_vidharbha", "Wardha": "mh_central_vidharbha",
        "Washim": "mh_central_vidharbha", "Yavatmal": "mh_central_vidharbha",
        "Bhandara": "mh_eastern_vidharbha", "Gadchiroli": "mh_eastern_vidharbha",
        "Gondia": "mh_eastern_vidharbha",
    },
    "West Bengal": {
        "Darjeeling": "wb_hilly",
        "Alipurduar": "wb_tarai", "Jalpaiguri": "wb_tarai",
        "Bardhaman": "wb_old_alluvial", "Hooghly": "wb_old_alluvial",
        "Dakshin Dinajpur": "wb_old_alluvial",
        "Coochbehar": "wb_new_alluvial", "Malda": "wb_new_alluvial",
        "Murshidabad": "wb_new_alluvial", "Nadia": "wb_new_alluvial",
        "Uttar-Dinajpur": "wb_new_alluvial",
        "Bankura": "wb_laterite", "Birbhum": "wb_laterite",
        "Purulia": "wb_laterite",
        "Howrah": "wb_coastal_saline", "North 24 parganas": "wb_coastal_saline",
        "South 24-Parganas": "wb_coastal_saline",
    },
}


def main():
    with open(ZONES_PATH) as f:
        zones = json.load(f)
    with open(DISTRICTS_PATH) as f:
        dist = json.load(f)

    # Build district-name -> id lookup per state.
    dmap = {}
    for s in dist["states"]:
        m = {}
        for x in s["districts"]:
            m[x["name"].lower()] = x["id"]
        dmap[s["state"]] = m

    zone_by_id = {z["id"]: z for z in zones["zones"]}

    def district_id(state, name):
        m = dmap[state]
        return m.get(name.lower())

    added = 0
    skipped_todo = []
    for state, assign in ZONE_ASSIGN.items():
        for cridaname, zone_key in assign.items():
            zid = ZONE_MAP[zone_key]
            lname = lgd_name(state, cridaname)
            did = district_id(state, lname)
            if did is None:
                skipped_todo.append((state, cridaname, "district-id-missing"))
                continue
            zone = zone_by_id[zid]
            if did not in [r["object"] for r in zone["relations"] if r.get("predicate") == "found_in"]:
                zone["relations"].append({"predicate": "found_in", "object": did})
                added += 1

    # Single-zone entities: whole state == the zone.
    whole_state = {
        "an_andaman": ("Andaman and Nicobar Islands", ["Nicobars", "North And Middle Andaman", "South Andamans"]),
        "ld_lakshadweep": ("Lakshadweep", ["Lakshadweep District"]),
        "py_puducherry": ("Puducherry", ["Karaikal", "Puducherry"]),
        "tm_north_east": ("Tripura", None),
    }
    for zone_key, (state, names) in whole_state.items():
        zid = ZONE_MAP[zone_key]
        zone = zone_by_id[zid]
        if names is None:
            names = [x["name"] for x in dmap[state].keys()] if False else [x["name"] for s2 in dist["states"] if s2["state"] == state for x in s2["districts"]]
        for n in names:
            did = district_id(state, n)
            if did and did not in [r["object"] for r in zone["relations"] if r.get("predicate") == "found_in"]:
                zone["relations"].append({"predicate": "found_in", "object": did})
                added += 1

    # Tripura + Mizoram + Manipur all belong to combined NEH zone.
    combined = zone_by_id[ZONE_MAP["tm_north_east"]]
    for state in ("Tripura", "Mizoram", "Manipur"):
        for x in [y for s2 in dist["states"] if s2["state"] == state for y in s2["districts"]]:
            did = x["id"]
            if did not in [r["object"] for r in combined["relations"] if r.get("predicate") == "found_in"]:
                combined["relations"].append({"predicate": "found_in", "object": did})
                added += 1

    with open(ZONES_PATH, "w") as f:
        json.dump(zones, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Added {added} found_in relations.")
    if skipped_todo:
        print("Skipped (TODO):", skipped_todo)


if __name__ == "__main__":
    main()
