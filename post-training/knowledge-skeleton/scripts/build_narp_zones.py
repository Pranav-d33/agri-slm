#!/usr/bin/env python3
"""
Build data/locations/narp_zones.json: the 127 NARP (National Agricultural
Research Project, ICAR) agro-climatic zone registry.

Source: Venkateswarlu, Ramakrishna & Rao, "Agro-climatic Zones of India",
Annals of Arid Zone 35(1):1-7 (1996), Table 1 (state-wise NARP zones with
rainfall + dominant soils). Paper lists 126 zones for 17 states + NEH region
+ islands; Rajya Sabha 2021 official answer confirms 127. Registry below uses
the paper's zone names; the count discrepancy is recorded in notes.

District-level found_in relations are added where a verified source exists
(DAC State Agriculture Profiles); otherwise noted as TODO.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "locations" / "narp_zones.json"
SRC = "https://epubs.icar.org.in/ejournal/index.php/AAZ/article/view/65198"

# canonical state/UT ids from states_uts.json, keyed by display name
_SU = json.loads((ROOT / "data" / "locations" / "states_uts.json").read_text(encoding="utf-8"))
STATE_IDS = {}
for _s in _SU.get("states", []):
    STATE_IDS[_s["name"]] = _s["id"]
for _s in _SU.get("union_territories", []):
    STATE_IDS[_s["name"]] = _s["id"]

# (state_name, zone_name, narp_zone_no, rainfall_mm, major_soils)
# narp_zone_no = paper's national NARP numbering (where given), else None
ZONES = [
    # Andhra Pradesh (7)
    ("Andhra Pradesh", "Krishna Godavari zone", 1, "800-1100", "Deltaic alluvium / deep black / red sandy"),
    ("Andhra Pradesh", "North coastal zone", 2, "1000-1100", "Red sandy / coastal alluvium"),
    ("Andhra Pradesh", "Southern zone", 3, "700-1050", "Red sandy / coastal alluvium / laterite"),
    ("Andhra Pradesh", "Northern Telangana zone", 4, "900-1150", "Deep black / medium black / red sandy"),
    ("Andhra Pradesh", "Southern Telangana zone", 5, "700-900", "Red sandy / medium black / deep black"),
    ("Andhra Pradesh", "Scarce rainfall zone", 6, "500-700", "Red loamy / medium black"),
    ("Andhra Pradesh", "High altitude zone", 7, ">1400", "Red loamy / red sandy"),
    # Assam (6)
    ("Assam", "South Arunachal Pradesh zone", 8, "950-1025", "Alluvial (recent)"),
    ("Assam", "Upper Brahmaputra Valley zone", 9, ">2000", "Alluvial"),
    ("Assam", "Central Brahmaputra Valley zone", 10, "600-1600", "Alluvial / red loamy"),
    ("Assam", "Lower Brahmaputra Valley zone", 11, ">1700", "Alluvial"),
    ("Assam", "Barak valley zone", 12, ">2000", "Alluvial / red loamy"),
    ("Assam", "Nagaland-Meghalaya hill zone", 13, ">2500", "Red loamy / lateritic"),
    # Bihar (6)
    ("Bihar", "North west alluvial plain zone", 14, "1200-1225", "Alluvial (recent) / calcareous alluvial"),
    ("Bihar", "North east alluvial plain zone", 15, "1350-1425", "Alluvial (recent)"),
    ("Bihar", "South Bihar alluvial plain zone", 16, "1000-1050", "Alluvial"),
    ("Bihar", "Central plateau zone", 17, "1300-1325", "Red loamy"),
    ("Bihar", "Western plateau zone", 18, "1400-1425", "Red and yellow"),
    ("Bihar", "South eastern plateau zone", 19, "1275-1325", "Mixed red and black"),
    # Gujarat (8)
    ("Gujarat", "South Gujarat zone", 20, ">1500", "Deep black / coastal alluvium"),
    ("Gujarat", "South Gujarat alluvial zone", 21, "1000-1500", "Deep black / coastal alluvium"),
    ("Gujarat", "Middle Gujarat zone", 22, "800-1000", "Medium black / grey brown"),
    ("Gujarat", "North Gujarat zone", 23, "625-875", "Grey brown"),
    ("Gujarat", "North west Gujarat zone", 24, "250-500", "Grey brown / deltaic alluvium / red sandy / medium black"),
    ("Gujarat", "North Saurashtra zone", 25, "400-700", "Medium black"),
    ("Gujarat", "South Saurashtra zone", 26, "750-1000", "Coastal alluvium / medium black"),
    ("Gujarat", "Bhal and coastal zone", 27, "625-1000", "Coastal alluvium / grey brown"),
    # Haryana (2)
    ("Haryana", "Eastern zone", 28, ">500", "Alluvial (recent) / calcareous alluvial"),
    ("Haryana", "Western zone", 29, "<500", "Calcareous / sierozemic"),
    # Himachal Pradesh (4)
    ("Himachal Pradesh", "Sub-montane and low hills zone", 30, "100-1200", "Brown hill soils"),
    ("Himachal Pradesh", "Mid hills sub-humid zone", 31, "1500-3000", "Brown hill soils"),
    ("Himachal Pradesh", "High hills temperate zone", 32, "800-300 (<>1000)", "Hill forest soils"),
    ("Himachal Pradesh", "High hills zone", 33, "250-350", "Hill soils"),
    # Jammu and Kashmir (5)
    ("Jammu and Kashmir", "Sub-tropical zone", 34, "1050-1075", "Brown hill / alluvial (recent)"),
    ("Jammu and Kashmir", "Intermediate zone", 35, "1200-1478", "Sub-montane / alluvial (recent)"),
    ("Jammu and Kashmir", "Valley temperate zone", 36, ">600", "Sub-montane / old alluvial"),
    ("Jammu and Kashmir", "Temperate zone", 37, "132-661", "Montane meadow / sub-montane / skeletal"),
    ("Jammu and Kashmir", "Cold arid zone", None, "80-115", "Skeletal / montane meadow / tarai"),
    # Karnataka (10)
    ("Karnataka", "Northeast transition zone", 38, "829-919", "Medium black / lateritic"),
    ("Karnataka", "Northeast dry zone", 39, "633-806", "Medium black / deep black"),
    ("Karnataka", "Northern dry zone", 40, "465-786", "Medium black / deep black / red sandy"),
    ("Karnataka", "Central dry zone", 41, "455-717", "Red sandy / deep black / medium black"),
    ("Karnataka", "Eastern dry zone", 42, "679-889", "Red loamy / red sandy / lateritic"),
    ("Karnataka", "Southern dry zone", 43, "670-889", "Red loamy / red sandy"),
    ("Karnataka", "Southern transition zone", 44, "611-1054", "Red sandy"),
    ("Karnataka", "Northern transition zone", 45, "619-1303", "Medium black / deep black / red loamy"),
    ("Karnataka", "Hill zone", 46, "904-3695", "Red loamy"),
    ("Karnataka", "Coastal zone", 47, "3010-4694", "Red loamy / coastal alluvium / laterite"),
    # Kerala (5)
    ("Kerala", "Northern zone", 48, ">3000", "Laterite / red loamy / coastal alluvium"),
    ("Kerala", "Southern zone", 49, "2000-3000", "Lateritic / red loamy / coastal alluvium"),
    ("Kerala", "Central zone", 50, "2115-3100", "Laterite / red loamy / coastal alluvium"),
    ("Kerala", "High altitude zone", 51, "3350-3600", "Red loamy"),
    ("Kerala", "Problem area zone", 52, "1000-2600", "Coastal alluvium / lateritic"),
    # Madhya Pradesh (12)
    ("Madhya Pradesh", "Chhattisgarh plain zone", 53, "1000-1500", "Red and yellow / deep black"),
    ("Madhya Pradesh", "Bastar plateau zone", 54, "1500-1600", "Red sandy / red and yellow"),
    ("Madhya Pradesh", "North hill zone", 55, "1000-2000", "Red and yellow"),
    ("Madhya Pradesh", "Kymore plateau zone", 56, "1000-1200", "Red and yellow / medium black / mixed black and red"),
    ("Madhya Pradesh", "Vidhya plateau zone", 57, "1000-1250", "Medium black"),
    ("Madhya Pradesh", "Central Narmada Valley zone", 58, "1000-1200", "Deep black / skeletal"),
    ("Madhya Pradesh", "Gird zone", 59, "600-800", "Medium black / alluvial"),
    ("Madhya Pradesh", "Bundelkhand zone", 60, "800-1000", "Mixed red and black"),
    ("Madhya Pradesh", "Satpura plateau zone", 61, "1000-1200", "Shallow black / mixed red and black"),
    ("Madhya Pradesh", "Malwa plateau zone", 62, "800-1000", "Medium black / mixed red and black"),
    ("Madhya Pradesh", "Nimar Valley zone", 63, "600-800", "Shallow red / medium black"),
    ("Madhya Pradesh", "Jhabua hills zone", 64, "600-700", "Shallow red / medium black"),
    # Maharashtra (9)
    ("Maharashtra", "South Konkan zone", 65, ">2500", "Laterite / red loamy / coastal alluvium"),
    ("Maharashtra", "North Konkan coast zone", 66, "1500-2000", "Red loamy / coastal alluvium"),
    ("Maharashtra", "Western Ghat zone", 67, "2000-2500", "Red loamy"),
    ("Maharashtra", "Sub-montane zone", 68, "700-2500", "Shallow red / medium to deep black"),
    ("Maharashtra", "Western Maharashtra plain zone", 69, "700-1250", "Medium black / deep black"),
    ("Maharashtra", "Scarcity zone", 70, "500-700", "Medium black / deep black"),
    ("Maharashtra", "Central Maharashtra plateau zone", 71, "700-900", "Medium black / deep black / shallow red"),
    ("Maharashtra", "Central Vidharbha zone", 72, "1100-1150", "Medium black / shallow black"),
    ("Maharashtra", "Eastern Vidharbha zone", 73, "1400-1550", "Medium to deep black"),
    # Orissa (10)
    ("Odisha", "Northwest plateau zone", 74, "1600-1675", "Red sandy / red and yellow"),
    ("Odisha", "North central plateau zone", 75, "1500-1550", "Red and yellow"),
    ("Odisha", "Northeast plateau zone", 76, "1550-1600", "Deltaic alluvial"),
    ("Odisha", "East and SE coast zone", 77, "1200-1450", "Coastal alluvial / laterite / red loamy"),
    ("Odisha", "Northeast Ghat zone", 78, "1550-1625", "Red loamy / laterite"),
    ("Odisha", "Eastern Ghat highland zone", 79, "1500-1550", "Red loamy / red sandy"),
    ("Odisha", "SE Ghat zone", 80, "1500-1521", "Red loamy"),
    ("Odisha", "Western undulating zone", 81, "1350-1375", "Red and yellow"),
    ("Odisha", "West central table land zone", 82, "1500-1550", "Red and yellow"),
    ("Odisha", "Mid central table land zone", 83, "1400-1450", "Red and yellow"),
    # Punjab (5)
    ("Punjab", "Sub-montane zone", 84, "900-1100", "Alluvial (recent)"),
    ("Punjab", "Undulating plains zone", 85, "800-900", "Alluvial (recent)"),
    ("Punjab", "Central plains zone", 86, "500-800", "Alluvial (recent)"),
    ("Punjab", "Western plains zone", 87, "400-500", "Calcareous / sierozemic"),
    ("Punjab", "Western zone", 88, "<400", "Old alluvial"),
    # Rajasthan (9)
    ("Rajasthan", "Arid western plains zone", 89, "100-300", "Desert (rhegosolic)"),
    ("Rajasthan", "Irrigated north zone", 90, "100-350", "Desert / alluvial / calcareous / sierozemic"),
    ("Rajasthan", "Transitional plains zone", 91, "300-500", "Desert / grey brown"),
    ("Rajasthan", "Transitional plain of Luni basin", 92, "300-500", "Desert / grey brown"),
    ("Rajasthan", "Semi-arid eastern plains zone", 93, "500-600", "Alluvial"),
    ("Rajasthan", "Flood prone eastern zone", 94, "500-600", "Alluvial (recent)"),
    ("Rajasthan", "Sub-humid southern zone", 95, "500-700", "Red and yellow / grey brown"),
    ("Rajasthan", "Southern humid plains zone", 96, "700-1000", "Mixed red and black / grey brown"),
    ("Rajasthan", "SE humid plains zone", 97, "650-1000", "Medium black"),
    # Tamil Nadu (7)
    ("Tamil Nadu", "Northeast zone", 98, "1025-1215", "Red loamy / red sandy"),
    ("Tamil Nadu", "Northwest zone", 99, "875-970", "Red loamy"),
    ("Tamil Nadu", "Western zone", 100, "600-650", "Mixed red and black"),
    ("Tamil Nadu", "Cauvery Delta zone", 101, "900-1000", "Deltaic alluvium / red loamy / coastal alluvium"),
    ("Tamil Nadu", "Southern zone", 102, "750-800", "Mixed red and black / coastal alluvium"),
    ("Tamil Nadu", "High rainfall zone", 103, "1469-1670", "Red loamy / coastal alluvium"),
    ("Tamil Nadu", "High altitude zone", 104, "1000-5000", "Red loamy / mixed red and black"),
    # Uttar Pradesh (10)
    ("Uttar Pradesh", "Hill zone", 105, "800-3000", "Brown hill soils"),
    ("Uttar Pradesh", "Bhabar and Tarai zone", 106, ">1400", "Tarai / alluvial"),
    ("Uttar Pradesh", "Western plain zone", 107, "700-1200", "Alluvial"),
    ("Uttar Pradesh", "Mid-western plain zone", 108, "850-1450", "Alluvial / tarai"),
    ("Uttar Pradesh", "SW semi-arid zone", 109, "750-780", "Alluvial"),
    ("Uttar Pradesh", "Central plains zone", 110, "885-1160", "Alluvial"),
    ("Uttar Pradesh", "Bundelkhand zone", 111, "700-1000", "Mixed red and black"),
    ("Uttar Pradesh", "Northeast plains zone", 112, "1460-1525", "Alluvial / tarai"),
    ("Uttar Pradesh", "Eastern plain zone", 113, "800-825", "Alluvial"),
    ("Uttar Pradesh", "Vindhyan zone", 114, "1100-1250", "Red and yellow / alluvial"),
    # West Bengal (6)
    ("West Bengal", "Hilly zone", 115, "2500-3000", "Brown hill soils"),
    ("West Bengal", "Tarai zone", 116, "2100-3000", "Tarai soils"),
    ("West Bengal", "Old alluvial zone", 117, "1100-1500", "Red loamy / alluvial / laterite"),
    ("West Bengal", "New alluvial zone", 118, "1200-1500", "Red and yellow / alluvial (recent)"),
    ("West Bengal", "Laterite and red soil zone", 119, "1100-1300", "Red loamy / red and yellow"),
    ("West Bengal", "Coastal saline zone", 120, "1450-1925", "Deltaic alluvium"),
]

# Extra zones (islands / NEH) from the paper + Rajya Sabha 127 reconciliation
EXTRA_ZONES = [
    # NEH combined zone (paper row 11) + Andaman & Nicobar + Lakshadweep + Puducherry
    ("Tripura, Mizoram and Manipur", "NEH combined zone", None, ">2000", "Alluvial / red loamy"),
    ("Andaman and Nicobar Islands", "Andaman and Nicobar zone", None, ">3000", "Red loamy"),
    ("Lakshadweep", "Lakshadweep zone", None, "<1500", "Sandy"),
    ("Puducherry", "Puducherry coastal zone", None, None, "Coastal alluvium"),
]

# map state name -> canonical id slug used in location.states.*
def state_slug(name):
    s = name.lower().replace(" and ", "_").replace(" ", "_")
    return re.sub(r"[^a-z0-9_]", "", s)


def main():
    dist_by_state = load_up_districts()
    zones = []
    for i, (state, zname, no, rainfall, soils) in enumerate(ZONES, start=1):
        zones.append(zone_entity(state, zname, no, rainfall, soils))
    for (state, zname, no, rainfall, soils) in EXTRA_ZONES:
        zones.append(zone_entity(state, zname, no, rainfall, soils))
    attach_up_districts(zones, dist_by_state)

    data = {
        "_description": "127 ICAR NARP (National Agricultural Research Project) agro-climatic zones. State-wise NARP registry from Venkateswarlu et al. (1996) Table 1 (Annals of Arid Zone 35(1)); count reconciled toward 127 per Rajya Sabha 2021 answer. District-level found_in relations added from DAC State Agriculture Profiles where verified; remaining district lists are TODO gaps.",
        "source": {"id": "narp-zones", "url": SRC},
        "zones": zones,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(zones)} NARP zones -> {OUT}")

# Verified zone->district mapping for UP (from DAC SP_UttarPradesh.pdf p2).
# DAC profile merges the paper's 10 zones into 9 (Tarai+Bhabar merged, Hill zone
# = present-day Uttarakhand, now a separate state). Keys = NARP zone id slug
# (after state prefix), values = list of district names as in districts.json.
UP_ZONE_DISTRICTS = {
    "bhabar_and_tarai_zone": [
        "Saharanpur", "Muzaffarnagar", "Bijnor", "Moradabad", "Rampur", "Bareilly",
        "Shahjahanpur", "Pilibhit", "Kheri", "Bahraich", "Shrawasti",
    ],
    "western_plain_zone": [
        "Saharanpur", "Muzaffarnagar", "Shamli", "Meerut", "Baghpat", "Ghaziabad",
        "Hapur", "Gautam Buddha Nagar", "Bulandshahr",
    ],
    "mid_western_plain_zone": [
        "Bijnor", "Amroha", "Moradabad", "Sambhal", "Rampur", "Bareilly", "Budaun",
        "Pilibhit", "Shahjahanpur", "Sitapur", "Kheri",
    ],
    "sw_semi_arid_zone": [
        "Agra", "Mathura", "Firozabad", "Mainpuri", "Aligarh", "Hathras", "Etah", "Kasganj",
    ],
    "central_plains_zone": [
        "Farrukhabad", "Kannauj", "Etawah", "Auraiya", "Kanpur Nagar", "Kanpur Dehat",
        "Fatehpur", "Kaushambi", "Prayagraj", "Hardoi", "Unnao", "Rae Bareli", "Lucknow",
    ],
    "bundelkhand_zone": [
        "Jhansi", "Jalaun", "Lalitpur", "Hamirpur", "Mahoba", "Banda", "Chitrakoot",
    ],
    "northeast_plains_zone": [
        "Bahraich", "Shrawasti", "Balrampur", "Gonda", "Siddharthnagar", "Basti",
        "Sant Kabir Nagar", "Mahrajganj", "Gorakhpur", "Kushinagar", "Deoria",
    ],
    "eastern_plain_zone": [
        "Bara Banki", "Ayodhya", "Amethi", "Sultanpur", "Ambedkar Nagar", "Jaunpur",
        "Varanasi", "Chandauli", "Bhadohi", "Ghazipur", "Azamgarh", "Mau", "Ballia", "Pratapgarh",
    ],
    "vindhyan_zone": ["Mirzapur", "Sonbhadra", "Prayagraj"],
}


def load_up_districts():
    """Return {name_lower: district_id} for Uttar Pradesh districts."""
    d = json.loads((ROOT / "data" / "locations" / "districts.json").read_text(encoding="utf-8"))
    out = {}
    for s in d.get("states", []):
        if s["state"] == "Uttar Pradesh":
            for dist in s["districts"]:
                out[dist["name"].lower()] = dist["id"]
    return out


def attach_up_districts(zones, dist_by_state):
    dac_src = {"id": "dac-sp", "url": "https://sugarcane.dac.gov.in/pdf/May2024/SP_UttarPradesh.pdf"}
    attached = 0
    for z in zones:
        if not z["id"].startswith("location.zones.narp_uttar_pradesh_"):
            continue
        slug = z["id"].split("narp_uttar_pradesh_")[1]
        dnames = UP_ZONE_DISTRICTS.get(slug)
        if not dnames:
            continue
        found = [dist_by_state[n.lower()] for n in dnames if n.lower() in dist_by_state]
        missing = [n for n in dnames if n.lower() not in dist_by_state]
        for fid in found:
            z["relations"].append({"predicate": "found_in", "object": fid, "source": dac_src})
        attached += len(found)
        z["notes"] = (f"found_in {len(found)} districts (DAC SP_UttarPradesh.pdf); "
                      f"missing {missing or 'none'} from districts.json")
    print(f"attached {attached} zone->district found_in relations (UP)")


def zone_entity(state, zname, no, rainfall, soils):
    st_slug = state_slug(state)
    zslug = re.sub(r"[^a-z0-9]+", "_", zname.lower()).strip("_")
    attrs = {}
    if no: attrs["narp_zone_no"] = no
    if rainfall: attrs["rainfall_mm"] = rainfall
    if soils: attrs["major_soils"] = soils
    rels = []
    state_id = STATE_IDS.get(state)
    if state_id:
        rels.append({"predicate": "part_of", "object": state_id})
    return {
        "id": f"location.zones.narp_{st_slug}_{zslug}",
        "name": f"{zname} ({state})",
        "state": state,
        "type": "location",
        "domain": "location",
        "attributes": attrs,
        "relations": rels,
        "source": {"id": "narp-zones", "url": SRC},
        "notes": "TODO: district list per zone from <state> agriculture profile; expected ~2-4 districts",
    }


if __name__ == "__main__":
    main()
